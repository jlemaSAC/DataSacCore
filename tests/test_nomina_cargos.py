from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.nomina.cargos.dependencies import get_cargo_service
from app.modules.nomina.cargos.schemas import CargoResponse


client = TestClient(app)


def test_listar_cargos_requires_bearer_token() -> None:
    response = client.get("/nomina/cargos")

    assert response.status_code == 401


def test_listar_cargos_returns_all_by_default() -> None:
    auth_context = object()

    class FakeCargoService:
        def list_cargos(
            self,
            auth_context: object,
            activo: bool | None = None,
        ) -> list[CargoResponse]:
            assert auth_context is auth_context_fixture
            assert activo is None
            return [
                CargoResponse(
                    id=7,
                    nombre="ASESOR DE CRÉDITO",
                    activo=True,
                    es_vinculado=False,
                )
            ]

    auth_context_fixture = auth_context
    app.dependency_overrides[get_current_auth_context] = lambda: auth_context
    app.dependency_overrides[get_cargo_service] = lambda: FakeCargoService()
    try:
        response = client.get("/nomina/cargos")
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_cargo_service, None)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 7,
            "nombre": "ASESOR DE CRÉDITO",
            "activo": True,
            "es_vinculado": False,
        }
    ]


def test_listar_cargos_passes_estado_filter() -> None:
    auth_context = object()

    class FakeCargoService:
        def list_cargos(
            self,
            auth_context: object,
            activo: bool | None = None,
        ) -> list[CargoResponse]:
            assert auth_context is auth_context_fixture
            assert activo is False
            return []

    auth_context_fixture = auth_context
    app.dependency_overrides[get_current_auth_context] = lambda: auth_context
    app.dependency_overrides[get_cargo_service] = lambda: FakeCargoService()
    try:
        response = client.get("/nomina/cargos?activo=false")
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_cargo_service, None)

    assert response.status_code == 200
    assert response.json() == []
