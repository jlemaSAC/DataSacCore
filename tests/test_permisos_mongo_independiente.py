from copy import deepcopy
from types import SimpleNamespace

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
import pytest

from app.modules.auth.repositories.atomic_menu_repository import AtomicMenuRepository
from app.modules.auth.repositories.mongo_menu_repository import MongoMenuRepository
from app.modules.auth.schemas import MenuDataSacWebCreateRequest, MenuDataSacWebUpdateRequest
from app.modules.seguridad.permisos.repositories.mongo_permiso_repository import MongoPermisoRepository, MongoPermisoWorkingRepository
from app.modules.seguridad.permisos.schemas import AccessBatchRequest, AccessChange
from test_seguridad_permisos import Collection, Database


class StateCollection(Collection):
    def insert_one(self, document, **kwargs):
        if self.find_one({'_id': document['_id']}):
            raise DuplicateKeyError('duplicate state')
        return super().insert_one(document, **kwargs)

    def replace_one(self, query, replacement, **kwargs):
        for index, document in enumerate(self.documents):
            if self._matches(document, query):
                self.documents[index] = deepcopy(replacement)
                return SimpleNamespace(matched_count=1)
        return SimpleNamespace(matched_count=0)


@pytest.fixture
def repos():
    database = Database()
    database.collections['menu_estado'] = StateCollection([])
    old = MongoMenuRepository(database)
    root = old.create_menu_node(MenuDataSacWebCreateRequest(label='Negocios', roles_codigo=[]))
    assigned = old.create_menu_node(MenuDataSacWebCreateRequest(label='Resumen', id_padre=root.id, tipo='ruta', roles_codigo=['002'], orden=1))
    empty = old.create_menu_node(MenuDataSacWebCreateRequest(label='Matriz', id_padre=root.id, tipo='ruta', roles_codigo=[], orden=2))
    return database, old, MongoPermisoRepository(database), root, assigned, empty


def grant(repo, menu_id, role, grant=True):
    return AccessBatchRequest(version=repo.get_snapshot().version, cambios=[AccessChange(menu_id=menu_id, rol_codigo=role, conceder=grant)])


def test_legacy_read_does_not_create_or_change_state(repos):
    database, old, repo, _, _, _ = repos
    before = {name: deepcopy(database[name].documents) for name in ('menu', 'permisos', 'rol_permisos')}
    assert repo.get_snapshot().menu == old.get_complete_menu_tree()
    assert repo.get_menu_by_role_codes(['002']) == old.get_menu_by_role_codes(['002'])
    assert database['menu_estado'].documents == []
    assert before == {name: database[name].documents for name in before}


def test_standalone_batch_is_atomic_and_shared_with_navigation(repos):
    database, old, repo, _, _, empty = repos
    original = {name: deepcopy(database[name].documents) for name in ('menu', 'permisos', 'rol_permisos')}
    snapshot, count = repo.apply_batch(grant(repo, empty.id, '002'))
    assert count == 1
    assert snapshot.menu[0].children[1].roles_directos_codigos == ['002']
    assert len(repo.get_menu_by_role_codes(['002'])[0].children) == 2
    assert len(AtomicMenuRepository(database).get_menu_by_role_codes(['002'])[0].children) == 2
    assert len(old.get_menu_by_role_codes(['002'])[0].children) == 1
    assert {name: database[name].documents for name in original} == original
    assert database['menu_estado'].find_one({'_id': 'actual'})['revision'] == 1


def test_menu_edits_and_grants_share_a_versioned_document(repos):
    database, _, repo, root, _, empty = repos
    repo.apply_batch(grant(repo, empty.id, '002'))
    manager = AtomicMenuRepository(database)
    manager.run_atomic(lambda working: working.update_menu_node(root.id, MenuDataSacWebUpdateRequest(label='Negocios nuevos')))
    tree = repo.get_snapshot().menu
    assert tree[0].codigo == 'NEGOCIOS_NUEVOS'
    assert tree[0].children[1].roles_directos_codigos == ['002']
    assert len(manager.get_menu_by_role_codes(['002'])[0].children) == 2
    assert database['menu_estado'].find_one({'_id': 'actual'})['revision'] == 2


def test_pending_request_fails_after_another_administrator_saves(repos):
    database, _, repo, _, _, empty = repos
    stale = grant(repo, empty.id, '002')
    repo.apply_batch(grant(repo, empty.id, '003'))
    before = deepcopy(database['menu_estado'].documents)
    with pytest.raises(HTTPException) as error:
        repo.apply_batch(stale)
    assert error.value.status_code == 409
    assert database['menu_estado'].documents == before


def test_mid_batch_failure_publishes_nothing(repos, monkeypatch):
    database, _, repo, _, _, empty = repos
    def fail(self, **kwargs):
        raise RuntimeError('failure before publication')
    monkeypatch.setattr(MongoPermisoWorkingRepository, '_sync_effective_role_permissions', fail)
    with pytest.raises(RuntimeError):
        repo.apply_batch(grant(repo, empty.id, '002'))
    assert database['menu_estado'].documents == []
    assert repo.get_snapshot().menu[0].children[1].roles_directos_codigos == []


def test_changed_legacy_data_is_detected_instead_of_silently_ignored(repos):
    database, _, repo, _, _, empty = repos
    repo.apply_batch(grant(repo, empty.id, '002'))
    database['menu'].documents[0]['label'] = 'Cambio externo'
    with pytest.raises(HTTPException) as error:
        repo.get_menu_by_role_codes(['002'])
    assert error.value.status_code == 503


def test_concurrent_compare_and_swap_cannot_overwrite_another_writer(repos, monkeypatch):
    database, _, repo, _, _, empty = repos
    repo.apply_batch(grant(repo, empty.id, '002'))
    original_replace = database['menu_estado'].replace_one
    def other_writer(query, replacement):
        database['menu_estado'].documents[0]['revision'] += 1
        return original_replace(query, replacement)
    monkeypatch.setattr(database['menu_estado'], 'replace_one', other_writer)
    with pytest.raises(HTTPException) as error:
        repo.apply_batch(grant(repo, empty.id, '003'))
    assert error.value.status_code == 409
    assert repo.get_snapshot().menu[0].children[1].roles_directos_codigos == ['002']


def test_oversized_state_is_rejected_before_any_write(repos, monkeypatch):
    database, _, repo, _, _, empty = repos
    monkeypatch.setattr(repo, 'max_state_bytes', 100)
    with pytest.raises(HTTPException) as error:
        repo.apply_batch(grant(repo, empty.id, '002'))
    assert error.value.status_code == 413
    assert database['menu_estado'].documents == []


def test_menu_delete_and_new_children_do_not_inherit_permissions(repos):
    database, _, repo, root, _, empty = repos
    repo.apply_batch(grant(repo, root.id, '002'))
    manager = AtomicMenuRepository(database)
    child = manager.run_atomic(lambda working: working.create_menu_node(MenuDataSacWebCreateRequest(label='Nuevo', id_padre=root.id, tipo='ruta', roles_codigo=[])))
    assert repo.get_snapshot().menu[0].children[-1].roles_directos_codigos == []
    manager.run_atomic(lambda working: working.delete_menu_node(child.id))
    assert all(item.id != child.id for item in repo.get_snapshot().menu[0].children)


def test_noop_does_not_create_a_new_state(repos):
    database, _, repo, _, assigned, _ = repos
    snapshot, count = repo.apply_batch(grant(repo, assigned.id, '002'))
    assert count == 0
    assert snapshot.menu[0].children[0].roles_directos_codigos == ['002']
    assert database['menu_estado'].documents == []


def test_error_after_migration_does_not_change_existing_state(repos, monkeypatch):
    database, _, repo, _, _, empty = repos
    repo.apply_batch(grant(repo, empty.id, '002'))
    before = deepcopy(database['menu_estado'].documents)
    request = grant(repo, empty.id, '003')
    def fail(self, **kwargs):
        raise RuntimeError('failure before CAS')
    monkeypatch.setattr(MongoPermisoWorkingRepository, '_sync_effective_role_permissions', fail)
    with pytest.raises(RuntimeError):
        repo.apply_batch(request)
    assert database['menu_estado'].documents == before
