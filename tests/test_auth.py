from datetime import date

from bson import ObjectId

from app.modules.auth.repositories.mongo_menu_repository import MongoMenuRepository
from app.modules.auth.security import JwtTokenService, PasswordHasher


class FakeMongoCollection:
    def __init__(self, documents: list[dict]) -> None:
        self.documents = documents
        self.last_filter = None

    def find(self, query: dict) -> list[dict]:
        self.last_filter = query
        role_codes = set(query["rolesPermitidosCodigos"]["$in"])
        return [
            document
            for document in self.documents
            if document.get("activo") is True
            and role_codes.intersection(document.get("rolesPermitidosCodigos", []))
        ]


class FakeMongoDatabase:
    def __init__(self, collection: FakeMongoCollection) -> None:
        self.collection = collection

    def __getitem__(self, name: str) -> FakeMongoCollection:
        assert name == "MenuPermisosDataSAC"
        return self.collection


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


def test_mongo_menu_repository_filters_by_roles_permitidos_codigos() -> None:
    parent_id = ObjectId()
    child_id = ObjectId()
    collection = FakeMongoCollection(
        [
            {
                "_id": parent_id,
                "label": "PROCESOS FINANCIEROS",
                "icon": "pi pi-caret-right",
                "idPadre": None,
                "routerLink": "/dashboard/procesos-financieros",
                "activo": True,
                "rolesPermitidosCodigos": ["001"],
            },
            {
                "_id": child_id,
                "label": "Cartera",
                "icon": "pi pi-circle",
                "idPadre": parent_id,
                "routerLink": "/dashboard/procesos-financieros/cartera",
                "activo": True,
                "rolesPermitidosCodigos": ["001"],
            },
            {
                "_id": ObjectId(),
                "label": "No permitido",
                "idPadre": None,
                "activo": True,
                "rolesPermitidosCodigos": ["999"],
            },
            {
                "_id": ObjectId(),
                "label": "Inactivo",
                "idPadre": None,
                "activo": False,
                "rolesPermitidosCodigos": ["001"],
            },
        ]
    )
    repository = MongoMenuRepository(FakeMongoDatabase(collection))

    menu = repository.get_menu_by_role_codes(["001"])

    assert collection.last_filter == {
        "activo": True,
        "rolesPermitidosCodigos": {"$in": ["001"]},
    }
    assert len(menu) == 1
    assert menu[0].label == "PROCESOS FINANCIEROS"
    assert len(menu[0].children) == 1
    assert menu[0].children[0].label == "Cartera"
