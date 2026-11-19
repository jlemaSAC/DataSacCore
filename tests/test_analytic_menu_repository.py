from unittest.mock import MagicMock

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pymongo import UpdateMany
import pytest

from app.modules.analytic.menu.dependencies import get_analytic_menu_service
from app.modules.analytic.menu.repositories.mongo_menu_repository import (
    MongoMenuAnalyticAdminRepository,
)
from app.modules.analytic.menu.router import router
from app.modules.analytic.menu.schemas import CambioAccesoAnalytic
from app.modules.analytic.menu.service import MenuAnalyticAdminService
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from test_auth import FakeMongoCollection, FakeMongoDatabase


def test_grupo_puede_tener_ruta() -> None:
    repository = MongoMenuAnalyticAdminRepository(MagicMock())

    repository._validar_documento_menu(
        {
            "tipo": "grupo",
            "ruta": "/analytic/indicadores-financieros",
        }
    )


def test_ruta_requiere_una_ruta() -> None:
    repository = MongoMenuAnalyticAdminRepository(MagicMock())

    with pytest.raises(HTTPException, match="debe tener ruta"):
        repository._validar_documento_menu({"tipo": "ruta", "ruta": None})


class AccessCursor(list):
    def sort(self, field, _direction):
        return sorted(self, key=lambda document: document[field])


class AccessCollection(FakeMongoCollection):
    def find(self, query, projection=None):
        return AccessCursor(super().find(query, projection))

    def bulk_write(self, operations, *, ordered):
        assert ordered
        for operation in operations:
            if isinstance(operation, UpdateMany):
                self.update_many(operation._filter, operation._doc)
            else:
                self.update_one(operation._filter, operation._doc, operation._upsert)


@pytest.fixture
def access_repository():
    root = ObjectId()
    route = ObjectId()
    hidden = ObjectId()
    menu = [
        {
            "_id": node, "codigo": code, "label": code, "id_padre": parent,
            "ruta": f"/dashboard/{code}", "tipo": kind, "activo": True,
            "orden": 1, "permiso_requerido": code + ".ver",
        }
        for node, code, parent, kind in [
            (root, "contable", None, "grupo"),
            (route, "saldo", root, "ruta"),
            (hidden, "oculto", root, "ruta"),
        ]
    ]
    permissions = [
        {"codigo": document["permiso_requerido"], "activo": document["_id"] != hidden}
        for document in menu
    ]
    relations = [
        {"_id": ObjectId(), "permiso_codigo": "contable.ver", "rol_codigo": "002", "activo": True},
        {"_id": ObjectId(), "permiso_codigo": "saldo.ver", "rol_codigo": "001", "activo": True},
        {"_id": ObjectId(), "permiso_codigo": "saldo.ver", "rol_codigo": "002", "activo": False},
    ]
    db = FakeMongoDatabase({
        "menu": AccessCollection(menu),
        "permisos": AccessCollection(permissions),
        "rol_permisos": AccessCollection(relations),
    })
    return MongoMenuAnalyticAdminRepository(db), str(root), str(route), str(hidden)


def test_access_batch_grants_and_revokes_existing_permissions_idempotently(access_repository):
    repository, root, route, _ = access_repository
    changes = [
        CambioAccesoAnalytic(menu_id=root, rol_codigo="003", conceder=True),
        CambioAccesoAnalytic(menu_id=route, rol_codigo="003", conceder=True),
        CambioAccesoAnalytic(menu_id=route, rol_codigo="002", conceder=True),
        CambioAccesoAnalytic(menu_id=route, rol_codigo="001", conceder=False),
    ]
    for _ in range(2):
        repository.save_access_changes(changes, {"001": "Admin", "002": "Analista", "003": "Contador"})

    tree, assignments = repository.get_access_state()
    assert [child.id for child in tree[0].children] == [route]
    assert assignments == {root: ["002", "003"], route: ["002", "003"]}
    assert [item.codigo for item in repository.get_menu_by_roles(["003"])[0].children] == ["saldo"]
    assert repository.get_menu_by_roles(["001"]) == []


def test_access_batch_validates_every_menu_before_writing(access_repository):
    repository, root, _, hidden = access_repository
    changes = [
        CambioAccesoAnalytic(menu_id=root, rol_codigo="003", conceder=True),
        CambioAccesoAnalytic(menu_id=hidden, rol_codigo="003", conceder=True),
    ]
    with pytest.raises(HTTPException) as error:
        repository.save_access_changes(changes, {"003": "Contador"})
    assert error.value.status_code == 409
    assert repository.get_access_state()[1][root] == ["002"]


def test_access_endpoints_require_bearer_and_admin():
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    sql = MagicMock()
    sql.get_roles_usuario.return_value = []
    service = MenuAnalyticAdminService(MagicMock(), MagicMock(), sql)
    app.dependency_overrides[get_analytic_menu_service] = lambda: service
    client = TestClient(app)
    body = {"cambios": [{"menu_id": "menu", "rol_codigo": "003", "conceder": True}]}
    assert client.get("/analytic/accesos").status_code == 401
    assert client.patch("/analytic/accesos", json=body).status_code == 401

    context = MagicMock(spec=AuthContext)
    context.usuario = MagicMock(sub="analista")
    app.dependency_overrides[get_current_auth_context] = lambda: context
    assert client.get("/analytic/accesos").status_code == 403
    assert client.patch("/analytic/accesos", json=body).status_code == 403
