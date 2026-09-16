from datetime import date

from bson import ObjectId
import pytest
from fastapi import HTTPException

from app.modules.auth.repositories.mongo_menu_repository import MongoMenuRepository
from app.modules.auth.schemas import MenuDataSacWebCreateRequest, MenuDataSacWebUpdateRequest
from app.modules.auth.security import JwtTokenService, PasswordHasher


class FakeMongoCollection:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = documents
        self.filters: list[dict] = []

    def find(self, query: dict, _projection: dict | None = None) -> list[dict]:
        self.filters.append(query)
        return [
            document
            for document in self.documents
            if self._matches(document, query)
        ]

    def find_one(self, query: dict) -> dict | None:
        return next((document for document in self.documents if self._matches(document, query)), None)

    def insert_one(self, document: dict):  # type: ignore[no-untyped-def]
        document.setdefault("_id", ObjectId())
        self.documents.append(document)

        class Result:
            inserted_id = document["_id"]

        return Result()

    def update_one(self, query: dict, update: dict, upsert: bool = False):  # type: ignore[no-untyped-def]
        document = self.find_one(query)
        if document is None and upsert:
            document = {field: value for field, value in query.items() if not isinstance(value, dict)}
            self.documents.append(document)
        if document is not None:
            document.update(update.get("$set", {}))
            for field, value in update.get("$setOnInsert", {}).items():
                document.setdefault(field, value)

    def update_many(self, query: dict, update: dict):  # type: ignore[no-untyped-def]
        for document in self.documents:
            if self._matches(document, query):
                document.update(update.get("$set", {}))

    @staticmethod
    def _matches(document: dict, query: dict) -> bool:
        for field, expected in query.items():
            actual = document.get(field)
            if isinstance(expected, dict):
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                if "$nin" in expected and actual in expected["$nin"]:
                    return False
            elif actual != expected:
                return False
        return True


class FakeMongoDatabase:
    def __init__(self, collections: dict[str, FakeMongoCollection]) -> None:
        self.collections = collections

    def __getitem__(self, name: str) -> FakeMongoCollection:
        return self.collections[name]


class FakeUsuario:
    usuario = "jdoe"
    nombre = "John Doe"
    id_agencia = 1


def test_password_hash_matches_datasac_service_strategy() -> None:
    assert PasswordHasher().generate_hash("001", "secret") == "HAPK2MNEYaDjaC+S5W/+frmaACM="


def test_jwt_token_service_creates_decodable_payload() -> None:
    token = JwtTokenService().create_access_token(FakeUsuario(), date(2026, 6, 12), "Matriz")

    payload = JwtTokenService().decode_access_token(token)

    assert payload.sub == "jdoe"
    assert payload.usuario == "John Doe"
    assert payload.id_agencia == 1
    assert payload.nombre_agencia == "Matriz"
    assert payload.fecha_sistema == date(2026, 6, 12)


def test_mongo_menu_repository_builds_menu_from_role_permissions() -> None:
    parent_id = ObjectId()
    child_id = ObjectId()
    menu_collection = FakeMongoCollection(
        [
            {
                "_id": parent_id,
                "codigo": "NEGOCIOS",
                "label": "NEGOCIOS",
                "icon": "pi pi-caret-right",
                "id_padre": None,
                "ruta": None,
                "permiso_requerido": "negocios.ver",
                "orden": 10,
                "activo": True,
            },
            {
                "_id": child_id,
                "codigo": "NEGOCIOS.COLOCACION",
                "label": "Colocacion",
                "icon": "pi pi-circle",
                "id_padre": parent_id,
                "ruta": "/dashboard/negocios/colocacion",
                "permiso_requerido": "negocios.colocacion.ver",
                "orden": 10,
                "activo": True,
            },
            {
                "_id": ObjectId(),
                "label": "No permitido",
                "id_padre": None,
                "permiso_requerido": "no-permitido.ver",
                "orden": 20,
                "activo": True,
            },
            {
                "_id": ObjectId(),
                "label": "Inactivo",
                "id_padre": None,
                "permiso_requerido": "inactivo.ver",
                "orden": 30,
                "activo": False,
            },
        ]
    )
    role_permissions_collection = FakeMongoCollection(
        [
            {"rol_codigo": "001", "permiso_codigo": "negocios.ver", "activo": True},
            {"rol_codigo": "001", "permiso_codigo": "negocios.colocacion.ver", "activo": True},
            {"rol_codigo": "001", "permiso_codigo": "inactivo.ver", "activo": False},
            {"rol_codigo": "999", "permiso_codigo": "no-permitido.ver", "activo": True},
        ]
    )
    permissions_collection = FakeMongoCollection(
        [
            {"codigo": "negocios.ver", "activo": True},
            {"codigo": "negocios.colocacion.ver", "activo": True},
            {"codigo": "inactivo.ver", "activo": False},
            {"codigo": "no-permitido.ver", "activo": True},
        ]
    )
    repository = MongoMenuRepository(
        FakeMongoDatabase(
            {
                "menu": menu_collection,
                "permisos": permissions_collection,
                "rol_permisos": role_permissions_collection,
            }
        )
    )

    menu = repository.get_menu_by_role_codes(["001"])

    assert role_permissions_collection.filters == [
        {"rol_codigo": {"$in": ["001"]}, "activo": True},
    ]
    assert permissions_collection.filters == [
        {
            "codigo": {"$in": ["negocios.colocacion.ver", "negocios.ver"]},
            "activo": True,
        },
    ]
    assert len(menu) == 1
    assert menu[0].label == "NEGOCIOS"
    assert len(menu[0].children) == 1
    assert menu[0].children[0].label == "Colocacion"
    assert menu[0].children[0].routerLink == "/dashboard/negocios/colocacion"


def test_mongo_menu_repository_returns_the_complete_tree_for_administration() -> None:
    parent_id = ObjectId()
    child_id = ObjectId()
    repository = MongoMenuRepository(
        FakeMongoDatabase(
            {
                "menu": FakeMongoCollection(
                    [
                        {
                            "_id": parent_id,
                            "codigo": "SEGURIDAD",
                            "label": "SEGURIDAD",
                            "id_padre": None,
                            "tipo": "grupo",
                            "ruta": None,
                            "permiso_requerido": "seguridad.ver",
                            "orden": 20,
                            "activo": True,
                        },
                        {
                            "_id": child_id,
                            "codigo": "SEGURIDAD.PERMISOS",
                            "label": "Permisos",
                            "id_padre": parent_id,
                            "tipo": "ruta",
                            "ruta": "/dashboard/seguridad/permisos",
                            "permiso_requerido": "seguridad.permisos.ver",
                            "orden": 10,
                            "activo": False,
                        },
                    ]
                ),
                "permisos": FakeMongoCollection([]),
                "rol_permisos": FakeMongoCollection(
                    [
                        {"rol_codigo": "001", "permiso_codigo": "seguridad.ver", "activo": True},
                        {"rol_codigo": "011", "permiso_codigo": "seguridad.permisos.ver", "activo": True},
                        {"rol_codigo": "999", "permiso_codigo": "seguridad.permisos.ver", "activo": False},
                    ]
                ),
            }
        )
    )

    menu = repository.get_complete_menu_tree()

    assert len(menu) == 1
    assert menu[0].codigo == "SEGURIDAD"
    assert menu[0].roles_directos_codigos == []
    assert menu[0].roles_permitidos_codigos == ["001"]
    assert menu[0].children[0].codigo == "SEGURIDAD.PERMISOS"
    assert menu[0].children[0].activo is False
    assert menu[0].children[0].roles_directos_codigos == ["011"]
    assert menu[0].children[0].roles_permitidos_codigos == ["011"]


def test_mongo_menu_repository_propagates_and_synchronizes_roles_to_all_ancestors() -> None:
    root_id = ObjectId()
    group_id = ObjectId()
    leaf_id = ObjectId()
    role_permissions = FakeMongoCollection(
        [
            {"_id": ObjectId(), "rol_codigo": "999", "permiso_codigo": "negocios.ver", "activo": True},
            {"_id": ObjectId(), "rol_codigo": "999", "permiso_codigo": "negocios.colocacion.ver", "activo": True},
            {"_id": ObjectId(), "rol_codigo": "001", "permiso_codigo": "negocios.colocacion.resumen.ver", "activo": True},
            {"_id": ObjectId(), "rol_codigo": "777", "permiso_codigo": "negocios.colocacion.resumen.ver", "activo": True},
        ]
    )
    repository = MongoMenuRepository(
        FakeMongoDatabase(
            {
                "menu": FakeMongoCollection(
                    [
                        {
                            "_id": root_id,
                            "codigo": "NEGOCIOS",
                            "label": "NEGOCIOS",
                            "id_padre": None,
                            "permiso_requerido": "negocios.ver",
                            "activo": True,
                        },
                        {
                            "_id": group_id,
                            "codigo": "NEGOCIOS.COLOCACION",
                            "label": "Colocacion",
                            "id_padre": root_id,
                            "permiso_requerido": "negocios.colocacion.ver",
                            "activo": True,
                        },
                        {
                            "_id": leaf_id,
                            "codigo": "NEGOCIOS.COLOCACION.RESUMEN",
                            "label": "Resumen",
                            "id_padre": group_id,
                            "permiso_requerido": "negocios.colocacion.resumen.ver",
                            "roles_directos_codigos": ["001", "002"],
                            "activo": True,
                        },
                    ]
                ),
                "permisos": FakeMongoCollection([]),
                "rol_permisos": role_permissions,
            }
        )
    )

    repository._sync_effective_role_permissions()

    assert {
        (item["permiso_codigo"], item["rol_codigo"])
        for item in role_permissions.documents
        if item["activo"]
    } == {
        ("negocios.ver", "001"),
        ("negocios.ver", "002"),
        ("negocios.colocacion.ver", "001"),
        ("negocios.colocacion.ver", "002"),
        ("negocios.colocacion.resumen.ver", "001"),
        ("negocios.colocacion.resumen.ver", "002"),
    }


def test_mongo_menu_repository_creates_hierarchical_code_permission_and_route() -> None:
    menu_collection = FakeMongoCollection([])
    repository = MongoMenuRepository(
        FakeMongoDatabase(
            {
                "menu": menu_collection,
                "permisos": FakeMongoCollection([]),
                "rol_permisos": FakeMongoCollection([]),
            }
        )
    )

    root = repository.create_menu_node(
        MenuDataSacWebCreateRequest(label="NEGOCIOS", roles_codigo=["001"])
    )
    child = repository.create_menu_node(
        MenuDataSacWebCreateRequest(label="Colocación", id_padre=root.id, roles_codigo=["001"])
    )
    leaf = repository.create_menu_node(
        MenuDataSacWebCreateRequest(label="Resumen", id_padre=child.id, tipo="ruta", roles_codigo=["001"])
    )

    assert leaf.codigo == "NEGOCIOS.COLOCACION.RESUMEN"
    assert leaf.permiso_requerido == "negocios.colocacion.resumen.ver"
    assert leaf.ruta == "/dashboard/negocios/colocacion/resumen"
    assert root.roles_directos_codigos == ["001"]
    assert root.roles_permitidos_codigos == ["001"]
    assert child.roles_directos_codigos == ["001"]
    assert child.roles_permitidos_codigos == ["001"]


def test_mongo_menu_repository_keeps_inherited_roles_out_of_the_parent_direct_assignment() -> None:
    repository = MongoMenuRepository(
        FakeMongoDatabase(
            {
                "menu": FakeMongoCollection([]),
                "permisos": FakeMongoCollection([]),
                "rol_permisos": FakeMongoCollection([]),
            }
        )
    )
    root = repository.create_menu_node(
        MenuDataSacWebCreateRequest(label="NEGOCIOS", roles_codigo=[])
    )
    child = repository.create_menu_node(
        MenuDataSacWebCreateRequest(
            label="Colocación",
            id_padre=root.id,
            roles_codigo=["002"],
        )
    )

    tree = repository.get_complete_menu_tree()
    assert tree[0].roles_directos_codigos == []
    assert tree[0].roles_permitidos_codigos == ["002"]

    # Simula abrir y guardar el padre: el formulario envia solo sus roles
    # directos, no los heredados del hijo.
    repository.update_menu_node(root.id, MenuDataSacWebUpdateRequest(roles_codigo=[]))
    repository.update_menu_node(child.id, MenuDataSacWebUpdateRequest(roles_codigo=[]))

    tree = repository.get_complete_menu_tree()
    assert tree[0].roles_directos_codigos == []
    assert tree[0].roles_permitidos_codigos == []


def test_mongo_menu_repository_rejects_changing_a_parent_to_route() -> None:
    repository = MongoMenuRepository(
        FakeMongoDatabase(
            {
                "menu": FakeMongoCollection([]),
                "permisos": FakeMongoCollection([]),
                "rol_permisos": FakeMongoCollection([]),
            }
        )
    )
    parent = repository.create_menu_node(MenuDataSacWebCreateRequest(label="SEGURIDAD"))
    repository.create_menu_node(
        MenuDataSacWebCreateRequest(label="Permisos", id_padre=parent.id)
    )

    with pytest.raises(HTTPException, match="con hijos debe mantenerse como tipo grupo") as error:
        repository.update_menu_node(parent.id, MenuDataSacWebUpdateRequest(tipo="ruta"))

    assert error.value.status_code == 400
