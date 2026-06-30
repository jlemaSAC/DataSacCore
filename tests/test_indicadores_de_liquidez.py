from datetime import date, datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.dependencies import (
    get_indicadores_de_liquidez_service,
)
from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.schemas import (
    InputIndicadoresDeLiquidez,
    InputIndicadoresDeLiquidezHistorico,
)
from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.service import (
    IndicadoresDeLiquidezService,
    construir_fechas_consulta,
    construir_fechas_consulta_diaria,
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
        return self.filas

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
            fecha_sistema=date(2026, 6, 18),
        ),
    )


def filas_liquidez(fecha_corte: date) -> list[dict]:
    saldos = {
        "11": 100.0,
        "13": 50.0,
        "21": 400.0,
        "2101": 200.0,
        "2103": 100.0,
        "210305": 25.0,
        "210310": 25.0,
    }
    return [
        {
            "Fecha": datetime.combine(fecha_corte, datetime.min.time()),
            "CodigoCuenta": codigo,
            "SaldoFinal": saldo,
        }
        for codigo, saldo in saldos.items()
    ]


def test_construir_fechas_consulta_usa_cierres_y_fecha_actual() -> None:
    fechas = construir_fechas_consulta(
        periodo_desde="2026-02",
        periodo_hasta="2026-06",
        hoy=date(2026, 6, 18),
    )

    assert fechas == [
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
        date(2026, 5, 31),
        date(2026, 6, 18),
    ]


def test_construir_fechas_consulta_rechaza_periodo_futuro() -> None:
    with pytest.raises(HTTPException) as exc_info:
        construir_fechas_consulta(
            periodo_desde="2026-06",
            periodo_hasta="2026-07",
            hoy=date(2026, 6, 18),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "No se pueden consultar periodos posteriores a la fecha actual."


def test_construir_fechas_consulta_rechaza_rango_invertido() -> None:
    with pytest.raises(HTTPException) as exc_info:
        construir_fechas_consulta(
            periodo_desde="2026-06",
            periodo_hasta="2026-05",
            hoy=date(2026, 6, 18),
        )

    assert exc_info.value.status_code == 400


def test_construir_fechas_consulta_diaria_incluye_todos_los_dias_de_dos_meses() -> None:
    fechas = construir_fechas_consulta_diaria(
        periodo_desde="2026-01",
        periodo_hasta="2026-02",
        hoy=date(2026, 6, 18),
    )

    assert fechas[0] == date(2026, 1, 1)
    assert fechas[-1] == date(2026, 2, 28)
    assert len(fechas) == 59


def test_construir_fechas_consulta_diaria_limita_mes_actual_a_hoy() -> None:
    fechas = construir_fechas_consulta_diaria(
        periodo_desde="2026-06",
        periodo_hasta="2026-06",
        hoy=date(2026, 6, 18),
    )

    assert fechas == [date(2026, 6, dia) for dia in range(1, 19)]


def test_servicio_devuelve_datos_y_reporta_periodos_sin_informacion(monkeypatch) -> None:
    repository = FakeSaldoContableRepository(
        filas=filas_liquidez(date(2026, 5, 31)) + filas_liquidez(date(2026, 6, 18))
    )
    service = IndicadoresDeLiquidezService(saldo_contable_repository=repository)
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.service."
        "fecha_actual_ecuador",
        lambda: date(2026, 6, 18),
    )

    response = service.consultar_indicadores_de_liquidez_historico(
        input_data=InputIndicadoresDeLiquidezHistorico(
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
    assert response.datos[0].fondos_disponibles_sobre_depositos_corto_plazo == 0.4
    assert response.datos[0].liquidez_sobre_obligaciones_publico == 0.25
    assert response.datos[0].liquidez_inversiones_sobre_depositos_vista_plazo == 0.5
    assert response.datos[0].inversiones_sobre_obligaciones_publico == 0.125
    assert response.datos[0].activos_liquidos_sobre_obligaciones_publico == 0.333333
    assert response.datos[0].liquidez_primera_linea is not None
    assert response.datos[0].liquidez_segunda_linea is not None


def test_endpoint_historico_devuelve_respuesta_mensual(monkeypatch) -> None:
    repository = FakeSaldoContableRepository(filas=filas_liquidez(date(2026, 6, 18)))
    service = IndicadoresDeLiquidezService(saldo_contable_repository=repository)
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.service."
        "fecha_actual_ecuador",
        lambda: date(2026, 6, 18),
    )
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_indicadores_de_liquidez_service] = lambda: service
    try:
        response = client.post(
            "/analytic/indicadores-financieros/indicadores-de-liquidez/historico-mensual",
            json={
                "periodo_desde": "2026-06",
                "periodo_hasta": "2026-06",
                "id_agencia": 1,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_indicadores_de_liquidez_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["periodo_desde"] == "2026-06"
    assert payload["periodo_hasta"] == "2026-06"
    assert payload["datos"][0]["fecha_corte"] == "2026-06-18"
    assert "inversiones_sobre_obligaciones_publico" in payload["datos"][0]
    assert "activos_liquidos_sobre_obligaciones_publico" in payload["datos"][0]
    assert "liquidez_primera_linea" in payload["datos"][0]
    assert "liquidez_segunda_linea" in payload["datos"][0]
    assert "saldos_cuentas" not in payload
    assert "componentes" not in payload


def test_endpoint_historico_rechaza_formato_de_periodo_invalido() -> None:
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    try:
        response = client.post(
            "/analytic/indicadores-financieros/indicadores-de-liquidez/historico-mensual",
            json={
                "periodo_desde": "2026-6",
                "periodo_hasta": "2026-06",
                "id_agencia": 1,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)

    assert response.status_code == 422


def test_endpoint_historico_diario_devuelve_dias_disponibles_hasta_hoy(monkeypatch) -> None:
    repository = FakeSaldoContableRepository(
        filas=filas_liquidez(date(2026, 6, 1)) + filas_liquidez(date(2026, 6, 18))
    )
    service = IndicadoresDeLiquidezService(saldo_contable_repository=repository)
    monkeypatch.setattr(
        "app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.service."
        "fecha_actual_ecuador",
        lambda: date(2026, 6, 18),
    )
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_indicadores_de_liquidez_service] = lambda: service
    try:
        response = client.post(
            "/analytic/indicadores-financieros/indicadores-de-liquidez/historico-diario",
            json={
                "periodo_desde": "2026-06",
                "periodo_hasta": "2026-06",
                "id_agencia": 1,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_indicadores_de_liquidez_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert [item["fecha_corte"] for item in payload["datos"]] == ["2026-06-01", "2026-06-18"]
    assert payload["periodos_sin_datos"][0] == "2026-06-02"
    assert payload["periodos_sin_datos"][-1] == "2026-06-17"
    assert len(repository.fechas) == 18


def test_endpoint_anterior_conserva_contrato_de_fecha_corte() -> None:
    fecha_corte = datetime(2026, 5, 31)
    repository = FakeSaldoContableRepository(filas=filas_liquidez(fecha_corte.date()))
    service = IndicadoresDeLiquidezService(saldo_contable_repository=repository)
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_indicadores_de_liquidez_service] = lambda: service
    try:
        response = client.post(
            "/analytic/indicadores-financieros/indicadores-de-liquidez",
            json={"fecha_corte": "2026-05-31T00:00:00", "id_agencia": 1},
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_indicadores_de_liquidez_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["fecha_corte"] == "2026-05-31T00:00:00"
    assert payload["indicadores"]["fondos_disponibles_sobre_depositos_corto_plazo"] == 0.4
    assert "saldos_cuentas" in payload
    assert "componentes" in payload
