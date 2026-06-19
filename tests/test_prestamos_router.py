from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.prestamos.dependencies import get_universo_prestamos_service
from app.modules.prestamos.schemas import (
    PrestamoSnapshot,
    PrestamoUniverseRequest,
    SituacionCrediticiaActualSyncRequest,
)
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
        self.indexes_created = False
        self.last_upsert_snapshots = None
        self.last_upsert_data_version = None

    def get_actual_snapshots(self, filtros: PrestamoUniverseRequest) -> list[PrestamoSnapshot]:
        self.last_actual_filters = filtros
        return self.actual

    def get_historico_snapshots(self, filtros: PrestamoUniverseRequest) -> list[PrestamoSnapshot]:
        self.last_historico_filters = filtros
        return self.historico

    def ensure_actual_indexes(self) -> None:
        self.indexes_created = True

    def upsert_actual_snapshots(
        self,
        snapshots: list[PrestamoSnapshot],
        *,
        as_of,
        data_version: str,
    ) -> dict[str, int]:
        _ = as_of
        self.last_upsert_snapshots = snapshots
        self.last_upsert_data_version = data_version
        return {"upserted": len(snapshots), "matched": 0, "modified": 0}


class FakeSqlUniversoRepository:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.last_limit = None

    def get_prestamos_actuales(self, *, limit: int | None = None) -> list[dict]:
        self.last_limit = limit
        return self.rows


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
        actual=[
            PrestamoSnapshot(
                numero_prestamo="0001",
                codigo_asesor="JPEREZ",
                saldo_capital=1000,
            )
        ],
        historico=[PrestamoSnapshot(numero_prestamo="0001", codigo_asesor="JPEREZ", saldo_capital=900)],
    )
    service = UniversoPrestamosService(repository=repository)

    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_universo_prestamos_service] = lambda: service
    try:
        response = client.post(
            "/prestamos/universo/buscar",
            json={
                "fecha_corte_anterior": "2026-05-31T00:00:00",
                "codigos_asesor": ["jperez"],
            },
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


def test_universo_prestamos_service_sincroniza_situacion_crediticia_actual() -> None:
    mongo_repository = FakeUniversoRepository()
    sql_repository = FakeSqlUniversoRepository(
        [
            {
                "IdPrestamo": 10,
                "NumeroPrestamo": "0001",
                "CodigoAsesor": "jperez",
                "SaldoCapital": "1000",
                "CapitalNoDevenga": "100",
                "CapitalVencido": "50",
                "DiasVencidos": "14",
                "EsDiferido": 1,
                "ExigibleCapital": "80",
                "ExigibleInteres": "12",
                "ExigibleMora": "3",
                "ExigibleOtros": "5",
                "ValorParaEstarAlDia": "100",
                "ValorHastaCuotaActual": "140",
                "ValorCancelarTotal": "1020",
            }
        ]
    )
    service = UniversoPrestamosService(repository=mongo_repository, sql_repository=sql_repository)

    response = service.sincronizar_situacion_crediticia_actual(
        request=SituacionCrediticiaActualSyncRequest(limit=1),
        auth_context=fake_auth_context(),
    )

    assert response.collection == "SituacionCrediticiaActual"
    assert response.total_leidos_sql == 1
    assert response.total_upserted == 1
    assert response.total_matched == 0
    assert response.total_modified == 0
    assert mongo_repository.indexes_created is True
    assert mongo_repository.last_upsert_snapshots[0].numero_prestamo == "0001"
    assert mongo_repository.last_upsert_snapshots[0].codigo_asesor == "JPEREZ"
    assert mongo_repository.last_upsert_snapshots[0].capital_no_devenga == 100
    assert mongo_repository.last_upsert_snapshots[0].capital_vencido == 50
    assert mongo_repository.last_upsert_snapshots[0].capital_vigente == 850
    assert mongo_repository.last_upsert_snapshots[0].dias_vencidos == 14
    assert mongo_repository.last_upsert_snapshots[0].es_diferido is True
    assert mongo_repository.last_upsert_snapshots[0].exigible_capital == 80
    assert mongo_repository.last_upsert_snapshots[0].exigible_interes == 12
    assert mongo_repository.last_upsert_snapshots[0].exigible_mora == 3
    assert mongo_repository.last_upsert_snapshots[0].exigible_otros == 5
    assert mongo_repository.last_upsert_snapshots[0].valor_para_estar_al_dia == 100
    assert mongo_repository.last_upsert_snapshots[0].valor_hasta_cuota_actual == 140
    assert mongo_repository.last_upsert_snapshots[0].valor_cancelar_total == 1020
    assert sql_repository.last_limit == 1


def test_prestamos_sincronizar_actual_endpoint_devuelve_conteos() -> None:
    mongo_repository = FakeUniversoRepository()
    sql_repository = FakeSqlUniversoRepository(
        [
            {
                "IdPrestamo": 10,
                "NumeroPrestamo": "0001",
                "CodigoAsesor": "jperez",
                "SaldoCapital": "1000",
                "CapitalNoDevenga": "100",
                "CapitalVencido": "50",
                "DiasVencidos": "14",
                "EsDiferido": 1,
                "ExigibleCapital": "80",
                "ExigibleInteres": "12",
                "ExigibleMora": "3",
                "ExigibleOtros": "5",
                "ValorParaEstarAlDia": "100",
                "ValorHastaCuotaActual": "140",
                "ValorCancelarTotal": "1020",
            }
        ]
    )
    service = UniversoPrestamosService(repository=mongo_repository, sql_repository=sql_repository)

    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_universo_prestamos_service] = lambda: service
    try:
        response = client.post(
            "/prestamos/universo/sincronizar-actual",
            json={"limit": 1},
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_universo_prestamos_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["collection"] == "SituacionCrediticiaActual"
    assert payload["total_leidos_sql"] == 1
    assert payload["total_upserted"] == 1
    assert payload["total_matched"] == 0
    assert payload["total_modified"] == 0


def test_prestamos_sincronizar_actual_requiere_limit_o_confirmacion_total() -> None:
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    try:
        response = client.post(
            "/prestamos/universo/sincronizar-actual",
            json={},
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)

    assert response.status_code == 422
