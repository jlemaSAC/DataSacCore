from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.prestamos.dependencies import get_universo_prestamos_service
from app.modules.prestamos.schemas import PrestamoSnapshot, PrestamoUniverseRequest
from app.modules.prestamos.service import UniversoPrestamosService


client = TestClient(app)


class FakeUniversoRepository:
    def __init__(
        self,
        actual: list[PrestamoSnapshot] | None = None,
        historico: list[PrestamoSnapshot] | None = None,
    ) -> None:
        self.actual = actual or []
        self.historico = historico or []
        self.last_actual_filters = None
        self.last_historico_filters = None

    def get_actual_snapshots(self, filtros: PrestamoUniverseRequest) -> list[PrestamoSnapshot]:
        self.last_actual_filters = filtros
        return self.actual

    def get_historico_snapshots(self, filtros: PrestamoUniverseRequest) -> list[PrestamoSnapshot]:
        self.last_historico_filters = filtros
        return self.historico


def fake_auth_context() -> AuthContext:
    return AuthContext.from_token_payload(
        "token",
        UsuarioTokenPayload(
            sub="jdoe",
            usuario="John Doe",
            id_agencia=1,
            nombre_agencia="Matriz",
            fecha_sistema=date(2026, 6, 18),
        ),
    )


def test_prestamos_universo_endpoint_requires_bearer_token() -> None:
    response = client.post("/prestamos/universo/buscar", json={})
    assert response.status_code == 401


def test_universo_prestamos_service_busca_actual_historico_y_conteos() -> None:
    repository = FakeUniversoRepository(
        actual=[PrestamoSnapshot(numero_prestamo="0001")],
        historico=[PrestamoSnapshot(numero_prestamo="0002"), PrestamoSnapshot(numero_prestamo="0003")],
    )
    service = UniversoPrestamosService(repository=repository)

    response = service.buscar_universo(
        filtros=PrestamoUniverseRequest(codigos_asesor=["jperez"]),
        auth_context=fake_auth_context(),
    )

    assert response.conteos.actual == 1
    assert response.conteos.historico == 2
    assert response.actual[0].numero_prestamo == "0001"
    assert response.historico[1].numero_prestamo == "0003"
    assert repository.last_actual_filters.codigos_asesor == ["jperez"]
    assert repository.last_historico_filters.codigos_asesor == ["jperez"]


def test_prestamos_universo_endpoint_devuelve_snapshots_normalizados() -> None:
    repository = FakeUniversoRepository(
        actual=[PrestamoSnapshot(numero_prestamo="0001", codigo_asesor="JPEREZ", saldo_capital=1000)],
        historico=[PrestamoSnapshot(numero_prestamo="0001", codigo_asesor="JPEREZ", saldo_capital=900)],
    )
    service = UniversoPrestamosService(repository=repository)

    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_universo_prestamos_service] = lambda: service
    try:
        response = client.post(
            "/prestamos/universo/buscar",
            json={"fecha_corte_anterior": "2026-05-31T00:00:00", "codigos_asesor": ["jperez"]},
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_universo_prestamos_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["conteos"] == {"actual": 1, "historico": 1}
    assert payload["actual"][0]["numero_prestamo"] == "0001"
    assert payload["actual"][0]["codigo_asesor"] == "JPEREZ"
    assert payload["actual"][0]["saldo_capital"] == 1000
    assert payload["historico"][0]["saldo_capital"] == 900


def test_sincronizar_actual_ya_no_esta_publicado_en_core() -> None:
    response = client.post("/prestamos/universo/sincronizar-actual", json={"limit": 1})
    assert response.status_code == 404
