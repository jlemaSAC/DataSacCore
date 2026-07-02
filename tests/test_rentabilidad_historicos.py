from datetime import date, datetime

from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.indicadores_financieros.rentabilidad.dependencies import (
    get_rentabilidad_service,
)
from app.modules.analytic.indicadores_financieros.rentabilidad.schemas import (
    InputRentabilidadHistorico,
)
from app.modules.analytic.indicadores_financieros.rentabilidad.service import (
    IndicadoresRentabilidadService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload


client = TestClient(app)


class FakeSaldoContableRepository:
    def __init__(self, filas: list[dict] | None = None) -> None:
        self.filas = filas or []
        self.consultas_fechas: list[list[datetime]] = []

    def get_saldos_contables_fechas_con_neteo(
        self,
        *,
        fechas: list[datetime],
        id_agencia: int,
        codigos_cuenta: list[str],
        neteo: int,
    ) -> list[dict]:
        _ = (id_agencia, neteo)
        self.consultas_fechas.append(fechas)
        return [
            fila
            for fila in self.filas
            if fila["Fecha"] in fechas and fila["CodigoCuenta"] in codigos_cuenta
        ]

    def get_saldos_contables_con_neteo(
        self,
        *,
        fecha: datetime,
        id_agencia: int,
        codigos_cuenta: list[str],
        neteo: int,
    ) -> list[dict]:
        _ = (id_agencia, neteo)
        return [
            {
                "CodigoCuenta": fila["CodigoCuenta"],
                "SaldoFinal": fila["SaldoFinal"],
            }
            for fila in self.filas
            if fila["Fecha"] == fecha and fila["CodigoCuenta"] in codigos_cuenta
        ]

    def get_promedios_saldos_contables_con_neteo(
        self,
        *,
        fecha_desde: datetime,
        fecha_hasta: datetime,
        id_agencia: int,
        codigos_cuenta: list[str],
        neteo: int,
    ) -> list[dict]:
        _ = (id_agencia, neteo)
        resultado: list[dict] = []
        for codigo in codigos_cuenta:
            valores = [
                float(fila["SaldoFinal"])
                for fila in self.filas
                if fecha_desde <= fila["Fecha"] <= fecha_hasta
                and fila["CodigoCuenta"] == codigo
            ]
            if valores:
                resultado.append(
                    {"CodigoCuenta": codigo, "SaldoPromedio": sum(valores) / len(valores)}
                )
        return resultado


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


def filas_para_fecha(fecha_corte: date, saldos: dict[str, float]) -> list[dict]:
    fecha = datetime.combine(fecha_corte, datetime.min.time())
    return [
        {"Fecha": fecha, "CodigoCuenta": codigo, "SaldoFinal": saldo}
        for codigo, saldo in saldos.items()
    ]


def saldos_corte() -> dict[str, float]:
    return {
        "51": 120.0,
        "41": 20.0,
        "45": 10.0,
        "5": 100.0,
        "4": 40.0,
        "14": 500.0,
        "1499": -50.0,
    }


def filas_rentabilidad() -> list[dict]:
    return (
        filas_para_fecha(
            date(2026, 1, 1),
            {"1": 1000.0, "3": 500.0, "21": 300.0, "26": 100.0},
        )
        + filas_para_fecha(
            date(2026, 6, 30),
            {
                **saldos_corte(),
                "1": 2000.0,
                "3": 700.0,
                "21": 500.0,
                "26": 100.0,
            },
        )
        + filas_para_fecha(
            date(2026, 7, 1),
            {
                **saldos_corte(),
                "1": 2200.0,
                "3": 800.0,
                "21": 600.0,
                "26": 100.0,
            },
        )
        + filas_para_fecha(
            date(2026, 7, 2),
            {
                **saldos_corte(),
                "1": 2400.0,
                "3": 900.0,
                "21": 700.0,
                "26": 100.0,
            },
        )
    )


def crear_servicio() -> tuple[IndicadoresRentabilidadService, FakeSaldoContableRepository]:
    repository = FakeSaldoContableRepository(filas_rentabilidad())
    return IndicadoresRentabilidadService(repository), repository


def test_servicio_rentabilidad_historico_mensual_calcula_promedio_por_corte(monkeypatch) -> None:
    service, repository = crear_servicio()
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.rentabilidad.service.fecha_actual_ecuador",
        lambda: date(2026, 7, 2),
    )

    response = service.consultar_rentabilidad_historico_mensual(
        input_data=InputRentabilidadHistorico(
            periodo_desde="2026-05",
            periodo_hasta="2026-07",
            id_agencia=1,
        ),
        auth_context=fake_auth_context(),
    )

    assert repository.consultas_fechas[0] == [
        datetime(2026, 5, 31),
        datetime(2026, 6, 30),
        datetime(2026, 7, 2),
    ]
    assert response.periodos_sin_datos == ["2026-05"]
    assert [item.fecha_corte for item in response.datos] == [date(2026, 6, 30), date(2026, 7, 2)]
    assert response.datos[0].gasto_operacional_sobre_margen_financiero_neto == 0.1
    assert response.datos[0].roa == 0.08
    assert response.datos[0].roe == 0.2
    assert response.datos[0].gasto_operativo_estimado_sobre_cartera_bruta == 0.036364
    assert response.datos[0].costo_promedio_fondeo == 0.08


def test_endpoint_rentabilidad_historico_diario(monkeypatch) -> None:
    service, repository = crear_servicio()
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.rentabilidad.service.fecha_actual_ecuador",
        lambda: date(2026, 7, 2),
    )
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_rentabilidad_service] = lambda: service
    try:
        response = client.post(
            "/analytic/indicadores-financieros/rentabilidad/historico-diario",
            json={
                "periodo_desde": "2026-07",
                "periodo_hasta": "2026-07",
                "id_agencia": 1,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_rentabilidad_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert [item["fecha_corte"] for item in payload["datos"]] == ["2026-07-01", "2026-07-02"]
    assert payload["periodos_sin_datos"] == []
    assert repository.consultas_fechas[0] == [datetime(2026, 7, 1), datetime(2026, 7, 2)]


def test_endpoint_rentabilidad_historico_rechaza_periodo_futuro(monkeypatch) -> None:
    service, _repository = crear_servicio()
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.rentabilidad.service.fecha_actual_ecuador",
        lambda: date(2026, 7, 2),
    )
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_rentabilidad_service] = lambda: service
    try:
        response = client.post(
            "/analytic/indicadores-financieros/rentabilidad/historico-mensual",
            json={
                "periodo_desde": "2026-07",
                "periodo_hasta": "2026-08",
                "id_agencia": 1,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_rentabilidad_service, None)

    assert response.status_code == 400


def test_endpoint_rentabilidad_anterior_conserva_contrato() -> None:
    service, _repository = crear_servicio()
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_rentabilidad_service] = lambda: service
    try:
        response = client.post(
            "/analytic/indicadores-financieros/rentabilidad",
            json={"fecha_corte": "2026-06-30T00:00:00", "id_agencia": 1},
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_rentabilidad_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["fecha_corte"] == "2026-06-30T00:00:00"
    assert payload["fecha_promedio_desde"] == "2026-01-01T00:00:00"
    assert payload["indicadores"]["roa"] == 0.08
    assert "saldos_promedio" in payload
    assert "componentes" in payload
