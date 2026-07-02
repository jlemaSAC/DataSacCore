from datetime import date, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.indicadores_financieros.calidad_de_activos.dependencies import (
    get_calidad_de_activos_service,
)
from app.modules.analytic.indicadores_financieros.calidad_de_activos.schemas import (
    InputCalidadDeActivosHistorico,
)
from app.modules.analytic.indicadores_financieros.calidad_de_activos.service import (
    IndicadoresCalidadDeActivosService,
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


def fake_auth_context() -> AuthContext:
    return AuthContext.from_token_payload(
        "token",
        UsuarioTokenPayload(
            sub="jdoe",
            usuario="John Doe",
            id_agencia=1,
            nombre_agencia="Matriz",
            fecha_sistema=date(2026, 7, 2),
        ),
    )


def filas_calidad_de_activos(fecha_corte: date) -> list[dict]:
    saldos = {
        "1": 1000.0,
        "11": 100.0,
        "14": 500.0,
        "1402": 100.0,
        "1426": 20.0,
        "1450": 10.0,
        "1499": -50.0,
    }
    fecha = datetime.combine(fecha_corte, datetime.min.time())
    return [
        {"Fecha": fecha, "CodigoCuenta": codigo, "SaldoFinal": saldo}
        for codigo, saldo in saldos.items()
    ]


def crear_servicio(
    filas: list[dict],
) -> tuple[IndicadoresCalidadDeActivosService, FakeSaldoContableRepository]:
    repository = FakeSaldoContableRepository(filas)
    return IndicadoresCalidadDeActivosService(repository), repository


def test_servicio_calidad_de_activos_historico_mensual(monkeypatch) -> None:
    service, repository = crear_servicio(
        filas_calidad_de_activos(date(2026, 6, 30))
        + filas_calidad_de_activos(date(2026, 7, 2))
    )
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.calidad_de_activos.service."
        "fecha_actual_ecuador",
        lambda: date(2026, 7, 2),
    )

    response = service.consultar_calidad_de_activos_historico_mensual(
        input_data=InputCalidadDeActivosHistorico(
            periodo_desde="2026-05",
            periodo_hasta="2026-07",
            id_agencia=1,
        ),
        auth_context=fake_auth_context(),
    )

    assert repository.fechas == [
        datetime(2026, 5, 31),
        datetime(2026, 6, 30),
        datetime(2026, 7, 2),
    ]
    assert response.periodos_sin_datos == ["2026-05"]
    assert [item.fecha_corte for item in response.datos] == [date(2026, 6, 30), date(2026, 7, 2)]
    assert response.datos[0].morosidad_ampliada == 0.230769
    assert response.datos[0].morosidad_consumo == 0.230769
    assert response.datos[0].activos_improductivos_netos_sobre_activo == 0.08
    assert response.datos[0].cartera_bruta_sobre_activos == 0.55
    assert response.datos[0].cobertura_cartera_en_riesgo == 1.666667


def test_endpoint_calidad_de_activos_historico_diario(monkeypatch) -> None:
    service, repository = crear_servicio(
        filas_calidad_de_activos(date(2026, 7, 1))
        + filas_calidad_de_activos(date(2026, 7, 2))
    )
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.calidad_de_activos.service."
        "fecha_actual_ecuador",
        lambda: date(2026, 7, 2),
    )
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_calidad_de_activos_service] = lambda: service
    try:
        response = client.post(
            "/analytic/indicadores-financieros/calidad-de-activos/historico-diario",
            json={
                "periodo_desde": "2026-07",
                "periodo_hasta": "2026-07",
                "id_agencia": 1,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_calidad_de_activos_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert [item["fecha_corte"] for item in payload["datos"]] == ["2026-07-01", "2026-07-02"]
    assert payload["periodos_sin_datos"] == []
    assert len(repository.fechas) == 2
    assert "cartera_refinanciada_restructurada_sobre_cartera_total" in payload["datos"][0]


def test_endpoint_calidad_de_activos_historico_rechaza_periodo_futuro(monkeypatch) -> None:
    service, _repository = crear_servicio([])
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.calidad_de_activos.service."
        "fecha_actual_ecuador",
        lambda: date(2026, 7, 2),
    )
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_calidad_de_activos_service] = lambda: service
    try:
        response = client.post(
            "/analytic/indicadores-financieros/calidad-de-activos/historico-mensual",
            json={
                "periodo_desde": "2026-07",
                "periodo_hasta": "2026-08",
                "id_agencia": 1,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_calidad_de_activos_service, None)

    assert response.status_code == 400


def test_endpoint_calidad_de_activos_anterior_conserva_contrato() -> None:
    service, _repository = crear_servicio(filas_calidad_de_activos(date(2026, 6, 30)))
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_calidad_de_activos_service] = lambda: service
    try:
        response = client.post(
            "/analytic/indicadores-financieros/calidad-de-activos",
            json={"fecha_corte": "2026-06-30T00:00:00", "id_agencia": 1},
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_calidad_de_activos_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["fecha_corte"] == "2026-06-30T00:00:00"
    assert payload["indicadores"]["morosidad_ampliada"] == 0.230769
    assert "saldos_cuentas" in payload
    assert "componentes" in payload
