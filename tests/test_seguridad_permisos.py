from copy import deepcopy
from datetime import date
from types import SimpleNamespace

from bson import ObjectId
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pymongo.errors import OperationFailure
import pytest

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, MenuDataSacWebCreateRequest, MenuDataSacWebUpdateRequest, UsuarioTokenPayload
from app.modules.auth.service import AuthService
from app.modules.seguridad.permisos.dependencies import get_permiso_service
from app.modules.seguridad.permisos.repositories.mongo_permiso_repository import MongoPermisoRepository
from app.modules.seguridad.permisos.schemas import AccessBatchRequest, AccessChange
from app.modules.seguridad.permisos.service import PermisoService
from test_auth import FakeMongoCollection


class Collection(FakeMongoCollection):
    def find(self, query, _projection=None, **kwargs):
        return deepcopy(super().find(query, _projection))

    def find_one(self, query, _projection=None, **kwargs):
        return deepcopy(super().find_one(query))

    def update_one(self, query, update, upsert=False, **kwargs):
        document = next((item for item in self.documents if self._matches(item, query)), None)
        if document is None and upsert:
            document = {**query, '_id': query.get('_id', ObjectId()), **update.get('$setOnInsert', {})}
            self.documents.append(document)
        if document is not None:
            document.update(update.get('$set', {}))
            for key, value in update.get('$inc', {}).items():
                document[key] = document.get(key, 0) + value

    def insert_one(self, document, **kwargs):
        return super().insert_one(deepcopy(document))

    def update_many(self, query, update, **kwargs):
        return super().update_many(query, update)


class Database:
    def __init__(self):
        self.collections = {key: Collection([]) for key in ('menu', 'permisos', 'rol_permisos', 'menu_admin_state')}
        self.client = self

    def __getitem__(self, key):
        return self.collections[key]

    def start_session(self):
        database = self
        class Session:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def with_transaction(self, callback, **kwargs):
                saved = {key: deepcopy(value.documents) for key, value in database.collections.items()}
                try:
                    return callback(self)
                except Exception:
                    for key, documents in saved.items():
                        database.collections[key].documents = documents
                    raise
        return Session()


@pytest.fixture
def repository():
    repo = MongoPermisoRepository(Database())
    root = repo.create_menu_node(MenuDataSacWebCreateRequest(label='Negocios', roles_codigo=[]))
    repo.create_menu_node(MenuDataSacWebCreateRequest(label='Resumen', id_padre=root.id, tipo='ruta', roles_codigo=['002']))
    repo.create_menu_node(MenuDataSacWebCreateRequest(label='Crédito', id_padre=root.id, tipo='ruta', orden=2, roles_codigo=[]))
    return repo


def batch(repository, changes):
    return AccessBatchRequest(version=repository.get_snapshot().version, cambios=changes)


def change(node, role='002', grant=True):
    return AccessChange(menu_id=node.id, rol_codigo=role, conceder=grant)


def test_batch_updates_both_perspectives_and_effective_navigation(repository):
    root = repository.get_snapshot().menu[0]
    leaf = root.children[1]
    snapshot, count = repository.apply_batch(batch(repository, [change(leaf)]))
    assert count == 1
    assert snapshot.menu[0].children[1].roles_directos_codigos == ['002']
    assert snapshot.menu[0].roles_directos_codigos == []
    assert snapshot.menu[0].roles_permitidos_codigos == ['002']
    authorized = repository.get_menu_by_role_codes(['002'])
    assert len(authorized[0].children) == 2
    # A future sibling never inherits the selected parent grant.
    repository.create_menu_node(MenuDataSacWebCreateRequest(label='Nuevo sensible', id_padre=root.id, roles_codigo=[]))
    assert len(repository.get_menu_by_role_codes(['002'])[0].children) == 2


def test_batch_revokes_leaf_without_revoking_sibling(repository):
    root = repository.get_snapshot().menu[0]
    repository.apply_batch(batch(repository, [change(root.children[0], grant=False)]))
    assert repository.get_menu_by_role_codes(['002']) == []
    assert repository.get_snapshot().menu[0].children[1].roles_directos_codigos == []


def test_parent_own_access_is_independent_from_descendants(repository):
    root = repository.get_snapshot().menu[0]
    repository.apply_batch(batch(repository, [change(root, grant=True)]))
    repository.apply_batch(batch(repository, [change(root, grant=False)]))
    state = repository.get_snapshot().menu[0]
    assert state.roles_directos_codigos == []
    assert state.roles_permitidos_codigos == ['002']
    assert state.children[1].roles_permitidos_codigos == []


def test_stale_batch_is_rejected_without_writes(repository):
    state = repository.get_snapshot()
    request = batch(repository, [change(state.menu[0].children[1])])
    repository.apply_batch(batch(repository, [change(state.menu[0], role='003')]))
    saved = deepcopy(repository.mongo_db['menu'].documents)
    with pytest.raises(HTTPException) as error:
        repository.apply_batch(request)
    assert error.value.status_code == 409
    assert repository.mongo_db['menu'].documents == saved


def test_batch_rolls_back_if_effective_sync_fails(repository, monkeypatch):
    root = repository.get_snapshot().menu[0]
    before = {key: deepcopy(collection.documents) for key, collection in repository.mongo_db.collections.items()}
    def fail(self, **kwargs):
        raise RuntimeError('simulated failure after direct updates')
    monkeypatch.setattr(MongoPermisoRepository, '_sync_effective_role_permissions', fail)
    with pytest.raises(RuntimeError):
        repository.apply_batch(batch(repository, [change(root.children[1])]))
    assert {key: collection.documents for key, collection in repository.mongo_db.collections.items()} == before


def test_all_menu_ids_validated_before_any_assignment(repository):
    root = repository.get_snapshot().menu[0]
    version = repository.get_snapshot().version
    with pytest.raises(HTTPException) as error:
        repository.apply_batch(batch(repository, [change(root.children[1]), AccessChange(menu_id=str(ObjectId()), rol_codigo='002', conceder=True)]))
    assert error.value.status_code == 404
    assert repository.get_snapshot().version == version


def test_duplicate_existing_relations_are_not_multiplied(repository):
    root = repository.get_snapshot().menu[0]
    collection = repository.mongo_db['rol_permisos']
    original = next(item for item in collection.documents if item['permiso_codigo'] == root.children[0].permiso_requerido)
    collection.insert_one({**original, '_id': ObjectId()})
    repository.apply_batch(batch(repository, [change(root.children[0], role='003')]))
    active = [(item['rol_codigo'], item['permiso_codigo']) for item in collection.documents if item['activo']]
    assert len(active) == len(set(active))


def test_legacy_grants_survive_metadata_and_code_edits(repository):
    root = repository.get_snapshot().menu[0]
    database = repository.mongo_db
    for document in database['menu'].documents:
        document.pop('roles_directos_codigos', None)
    database['rol_permisos'].insert_one({'rol_codigo': '003', 'permiso_codigo': root.permiso_requerido, 'activo': True})
    repository.run_atomic(lambda repo: repo.update_menu_node(root.id, MenuDataSacWebUpdateRequest(label='Negocios nuevos')))
    result = repository.get_snapshot().menu[0]
    assert result.roles_directos_codigos == ['003']
    assert result.roles_permitidos_codigos == ['002', '003']
    assert result.children[0].roles_directos_codigos == ['002']


def test_empty_difference_is_noop(repository):
    root = repository.get_snapshot().menu[0]
    before = repository.get_snapshot()
    after, count = repository.apply_batch(batch(repository, [change(root.children[0])]))
    assert count == 0
    assert before.version == after.version


def test_unsupported_transactions_fail_closed(repository, monkeypatch):
    def fail():
        raise OperationFailure('transactions unsupported', code=20)
    monkeypatch.setattr(repository.mongo_db, 'start_session', fail)
    with pytest.raises(HTTPException) as error:
        repository.apply_batch(AccessBatchRequest(version='0' * 64, cambios=[AccessChange(menu_id='x', rol_codigo='002', conceder=True)]))
    assert error.value.status_code == 503


def context():
    return AuthContext(token='test', usuario=UsuarioTokenPayload(sub='admin', usuario='admin', id_agencia=1, fecha_sistema=date(2026, 10, 27)))


class Roles:
    def list_roles(self):
        return [SimpleNamespace(codigo=code, nombre=code, nivel=1, activo=code != '004') for code in ['001', '002', '003', '004']]


def service(repository, admin=True):
    class Sql:
        def get_usuario(self, code):
            return SimpleNamespace(usuario=code, activo=True, puede_ingresar_sistema=True)
        def get_roles_usuario(self, code):
            return [SimpleNamespace(codigo='001' if admin else '002', nombre='Role', nivel=1, activo=True)]
    return PermisoService(repository, Roles(), AuthService(db=None, sql_repository=Sql()))


def test_admin_authorization_is_checked_against_sql(repository):
    for operation in ['get', 'save']:
        with pytest.raises(HTTPException) as error:
            svc = service(repository, admin=False)
            if operation == 'get':
                svc.get_state(context())
            else:
                svc.save(context(), batch(repository, [change(repository.get_snapshot().menu[0])]))
        assert error.value.status_code == 403


@pytest.mark.parametrize('role', ['missing', '004'])
def test_unknown_or_inactive_roles_cannot_receive_grants(repository, role):
    with pytest.raises(HTTPException) as error:
        service(repository).save(context(), batch(repository, [change(repository.get_snapshot().menu[0], role=role)]))
    assert error.value.status_code == 404


def test_duplicate_pairs_in_request_rejected(repository):
    item = change(repository.get_snapshot().menu[0])
    with pytest.raises(HTTPException) as error:
        service(repository).save(context(), batch(repository, [item, item]))
    assert error.value.status_code == 400


def test_endpoints_require_bearer():
    client = TestClient(app)
    assert client.get('/seguridad/permisos').status_code == 401
    assert client.patch('/seguridad/permisos', json={'version': '0' * 64, 'cambios': []}).status_code == 401


def test_endpoint_round_trip_preserves_one_shared_source(repository):
    client = TestClient(app)
    app.dependency_overrides[get_current_auth_context] = context
    app.dependency_overrides[get_permiso_service] = lambda: service(repository)
    try:
        original = client.get('/seguridad/permisos').json()
        leaf = original['menu'][0]['children'][1]
        response = client.patch('/seguridad/permisos', json={'version': original['version'], 'cambios': [{'menu_id': leaf['id'], 'rol_codigo': '003', 'conceder': True}]})
        assert response.status_code == 200
        assert response.json()['modificaciones'] == 1
        assert response.json()['menu'][0]['children'][1]['roles_directos_codigos'] == ['003']
        assert client.get('/seguridad/permisos').json()['version'] == response.json()['version']
        assert client.patch('/seguridad/permisos', json={'version': original['version'], 'cambios': [{'menu_id': leaf['id'], 'rol_codigo': '002', 'conceder': True}]}).status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_admin_navigation_exposes_both_tools_without_duplicate_links(repository):
    auth = service(repository).auth
    auth.menu_repository = repository
    menu = auth.build_menu_response('admin').menu
    section = next(item for item in menu if item.routerLink == '/dashboard/seguridad')
    assert {item.routerLink for item in section.children} == {
        '/dashboard/seguridad/menus', '/dashboard/seguridad/permisos',
    }
    auth._add_security_admin_navigation(menu)
    assert len(section.children) == 2
    ordinary = service(repository, admin=False).auth
    ordinary.menu_repository = repository
    assert all(item.routerLink != '/dashboard/seguridad' for item in ordinary.build_menu_response('user').menu)



def test_batch_does_not_rewrite_unrelated_existing_relations(repository):
    root = repository.get_snapshot().menu[0]
    unrelated = {'_id': ObjectId(), 'rol_codigo': 'legacy', 'permiso_codigo': root.children[1].permiso_requerido, 'activo': True}
    repository.mongo_db['rol_permisos'].insert_one(unrelated)
    repository.apply_batch(batch(repository, [change(root.children[0], grant=False)]))
    assert repository.mongo_db['rol_permisos'].find_one({'_id': unrelated['_id']}) == unrelated
