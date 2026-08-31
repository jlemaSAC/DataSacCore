from datetime import date

from bson import ObjectId

from app.modules.auth.repositories.mongo_menu_repository import MongoMenuRepository
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
            if all(
                document.get(field) is expected
                if not isinstance(expected, dict)
                else document.get(field) in expected.get("$in", [])
                for field, expected in query.items()
            )
        ]


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
    assert menu[0].roles_permitidos_codigos == ["001"]
    assert menu[0].children[0].codigo == "SEGURIDAD.PERMISOS"
    assert menu[0].children[0].activo is False
    assert menu[0].children[0].roles_permitidos_codigos == ["011"]
