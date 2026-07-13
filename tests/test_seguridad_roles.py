from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.seguridad.roles.dependencies import get_rol_service
from app.modules.seguridad.roles.schemas import RolResponse


client = TestClient(app)


def test_listar_roles_requires_bearer_token() -> None:
    response = client.get("/seguridad/roles")

    assert response.status_code == 401


def test_listar_roles_returns_all_by_default() -> None:
    auth_context_fixture = object()

    class FakeRolService:
        def list_roles(
            self,
            auth_context: object,
            activo: bool | None = None,
        ) -> list[RolResponse]:
            assert auth_context is auth_context_fixture
            assert activo is None
            return [
                RolResponse(
                    codigo="001",
                    nombre="ADMINISTRADOR",
                    nivel=1,
                    activo=True,
                )
            ]

    app.dependency_overrides[get_current_auth_context] = lambda: auth_context_fixture
    app.dependency_overrides[get_rol_service] = lambda: FakeRolService()
    try:
        response = client.get("/seguridad/roles")
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_rol_service, None)

    assert response.status_code == 200
    assert response.json() == [
        {
            "codigo": "001",
            "nombre": "ADMINISTRADOR",
            "nivel": 1,
            "activo": True,
        }
    ]


def test_listar_roles_passes_estado_filter() -> None:
    auth_context_fixture = object()

    class FakeRolService:
        def list_roles(
            self,
            auth_context: object,
            activo: bool | None = None,
        ) -> list[RolResponse]:
            assert auth_context is auth_context_fixture
            assert activo is False
            return []

    app.dependency_overrides[get_current_auth_context] = lambda: auth_context_fixture
    app.dependency_overrides[get_rol_service] = lambda: FakeRolService()
    try:
        response = client.get("/seguridad/roles?activo=false")
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_rol_service, None)

    assert response.status_code == 200
    assert response.json() == []
