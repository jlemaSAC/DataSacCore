from datetime import date, datetime

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.indicadores_financieros.solvencia.dependencies import (
    get_solvencia_service,
)
from app.modules.analytic.indicadores_financieros.solvencia.schemas import (
    InputSolvenciaHistorico,
)
from app.modules.analytic.indicadores_financieros.solvencia.service import (
    IndicadoresFinancierosService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload


client = TestClient(app)


class FakeSaldoContableRepository:
    def __init__(self, filas: list[dict] | None = None) -> None:
        self.filas = filas or []
        self.fechas: list[datetime] = []

    def get_saldos_contables_fechas_con_neteo(
        self,
        *,
        fechas: list[datetime],
        id_agencia: int,
        codigos_cuenta: list[str],
        neteo: int,
    ) -> list[dict]:
        _ = (id_agencia, codigos_cuenta, neteo)
        self.fechas = fechas
        return [fila for fila in self.filas if fila["Fecha"] in fechas]

    def get_saldos_contables_con_neteo(
        self,
        *,
        fecha: datetime,
        id_agencia: int,
        codigos_cuenta: list[str],
        neteo: int,
    ) -> list[dict]:
        _ = (id_agencia, codigos_cuenta, neteo)
        self.fechas = [fecha]
        return [
            {
                "CodigoCuenta": fila["CodigoCuenta"],
                "SaldoFinal": fila["SaldoFinal"],
            }
            for fila in self.filas
            if fila["Fecha"] == fecha
        ]


class FakeSqlSolvenciaRepository:
    def get_nombre_agencia(self, id_agencia: int) -> None:
        _ = id_agencia
        return None

    def get_ids_prestamos_activos(self, id_agencia: int) -> list[int]:
        _ = id_agencia
        return []

    def sum_provision_requerida_viva(
        self,
        *,
        ids_prestamos: list[int],
        fecha_consulta: datetime,
    ) -> float:
        _ = (ids_prestamos, fecha_consulta)
        return 0.0


class FakeMongoSolvenciaRepository:
    def __init__(self, fechas_sin_datos: set[date] | None = None) -> None:
        self.fechas_sin_datos = fechas_sin_datos or set()

    def get_provision_requerida_situacion_crediticia(
        self,
        *,
        fecha_corte: datetime,
        nombre_agencia: str | None,
    ) -> float:
        _ = nombre_agencia
        if fecha_corte.date() in self.fechas_sin_datos:
            raise HTTPException(
                status_code=422,
                detail="No hay datos en SituacionCrediticia para la fecha solicitada.",
            )
        return 0.0


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


def filas_solvencia(fecha_corte: date) -> list[dict]:
    saldos = {
        "1": 1000.0,
        "3": 200.0,
        "11": 100.0,
        "13": 400.0,
        "18": 50.0,
        "31": 100.0,
    }
    fecha = datetime.combine(fecha_corte, datetime.min.time())
    return [
        {"Fecha": fecha, "CodigoCuenta": codigo, "SaldoFinal": saldo}
        for codigo, saldo in saldos.items()
    ]


def crear_servicio(
    filas: list[dict],
    *,
    fechas_sin_provisiones: set[date] | None = None,
) -> tuple[IndicadoresFinancierosService, FakeSaldoContableRepository]:
    saldo_repository = FakeSaldoContableRepository(filas)
    return (
        IndicadoresFinancierosService(
            saldo_contable_repository=saldo_repository,
            sql_repository=FakeSqlSolvenciaRepository(),
            mongo_repository=FakeMongoSolvenciaRepository(fechas_sin_provisiones),
        ),
        saldo_repository,
    )


def test_servicio_solvencia_historico_mensual_usa_cierres_y_fecha_actual(monkeypatch) -> None:
    service, repository = crear_servicio(
        filas_solvencia(date(2026, 5, 31)) + filas_solvencia(date(2026, 6, 18))
    )
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.solvencia.service.fecha_actual_ecuador",
        lambda: date(2026, 6, 18),
    )

    response = service.consultar_solvencia_historico_mensual(
        input_data=InputSolvenciaHistorico(
            periodo_desde="2026-04",
            periodo_hasta="2026-06",
            id_agencia=1,
        ),
        auth_context=fake_auth_context(),
    )

    assert repository.fechas == [
        datetime(2026, 4, 30),
        datetime(2026, 5, 31),
        datetime(2026, 6, 18),
    ]
    assert response.periodos_sin_datos == ["2026-04"]
    assert [item.fecha_corte for item in response.datos] == [date(2026, 5, 31), date(2026, 6, 18)]
    assert response.datos[0].solvencia == 0.222222
    assert response.datos[0].activos_fijos_sobre_patrimonio_tecnico == 0.5
    assert response.datos[0].patrimonio_sobre_activo == 0.2
    assert response.datos[0].patrimonio_resultados_sobre_activos_improductivos_netos == 1.333333


def test_endpoint_solvencia_historico_diario_devuelve_dias_disponibles(monkeypatch) -> None:
    service, repository = crear_servicio(
        filas_solvencia(date(2026, 6, 1)) + filas_solvencia(date(2026, 6, 18))
    )
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.solvencia.service.fecha_actual_ecuador",
        lambda: date(2026, 6, 18),
    )
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_solvencia_service] = lambda: service
    try:
        response = client.post(
            "/analytic/indicadores-financieros/solvencia/historico-diario",
            json={
                "periodo_desde": "2026-06",
                "periodo_hasta": "2026-06",
                "id_agencia": 1,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_solvencia_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert [item["fecha_corte"] for item in payload["datos"]] == ["2026-06-01", "2026-06-18"]
    assert payload["periodos_sin_datos"][0] == "2026-06-02"
    assert payload["periodos_sin_datos"][-1] == "2026-06-17"
    assert len(repository.fechas) == 18


def test_historico_solvencia_reporta_fecha_sin_provisiones_como_sin_datos(monkeypatch) -> None:
    service, _repository = crear_servicio(
        filas_solvencia(date(2026, 5, 31)),
        fechas_sin_provisiones={date(2026, 5, 31)},
    )
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.solvencia.service.fecha_actual_ecuador",
        lambda: date(2026, 6, 18),
    )

    response = service.consultar_solvencia_historico_mensual(
        input_data=InputSolvenciaHistorico(
            periodo_desde="2026-05",
            periodo_hasta="2026-05",
            id_agencia=1,
        ),
        auth_context=fake_auth_context(),
    )

    assert response.datos == []
    assert response.periodos_sin_datos == ["2026-05"]


def test_endpoint_solvencia_historico_rechaza_periodo_futuro(monkeypatch) -> None:
    service, _repository = crear_servicio([])
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.solvencia.service.fecha_actual_ecuador",
        lambda: date(2026, 6, 18),
    )
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_solvencia_service] = lambda: service
    try:
        response = client.post(
            "/analytic/indicadores-financieros/solvencia/historico-mensual",
            json={
                "periodo_desde": "2026-06",
                "periodo_hasta": "2026-07",
                "id_agencia": 1,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_solvencia_service, None)

    assert response.status_code == 400


def test_endpoint_solvencia_anterior_conserva_contrato() -> None:
    service, _repository = crear_servicio(filas_solvencia(date(2026, 5, 31)))
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_solvencia_service] = lambda: service
    try:
        response = client.post(
            "/analytic/indicadores-financieros/solvencia",
            json={
                "fecha_corte": "2026-05-31T00:00:00",
                "id_agencia": 1,
                "deficiencia": 0,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_solvencia_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["fecha_corte"] == "2026-05-31T00:00:00"
    assert payload["indicadores"]["solvencia"] == 0.222222
    assert "saldos_cuentas" in payload
    assert "componentes" in payload
