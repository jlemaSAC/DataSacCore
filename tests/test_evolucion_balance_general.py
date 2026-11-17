from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.analytic.evolucion_cuentas.router import router
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general import schemas
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.dependencies import get_evolucion_balance_service
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import ConsultaEvolucionBalance
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.service import EvolucionBalanceService


@pytest.fixture(autouse=True)
def fecha_fija(monkeypatch):
    monkeypatch.setattr(schemas, "fecha_actual_ecuador", lambda: date(2026, 11, 17))


class Repositorio:
    def __init__(self, filas=()):
        self.filas = list(filas)
        self.consultas = []

    def obtener_agencia(self, id_agencia):
        return dict(nombre="CONSOLIDADO" if id_agencia == 1 else "MATRIZ", id_empresa=1) if id_agencia in (1, 2) else None

    def obtener_saldos_fechas(self, **kwargs):
        self.consultas.append(kwargs)
        return self.filas


def fila(fecha, codigo, saldo):
    return dict(fecha=date.fromisoformat(fecha), codigo_cuenta=codigo, saldo=Decimal(saldo))


@pytest.mark.parametrize("inicio,fin,fechas", [
    ("2024-01-01", "2024-03-31", ["2024-01-31", "2024-02-29", "2024-03-31"]),
    ("2025-12-10", "2026-02-28", ["2025-12-31", "2026-01-31", "2026-02-28"]),
    ("2026-01-01", "2026-03-15", ["2026-01-31", "2026-02-28"]),
    ("2026-10-31", "2026-10-31", ["2026-10-31"]),
    ("2026-09-01", "2026-11-17", ["2026-09-30", "2026-10-31", "2026-11-17"]),
    ("2026-11-01", "2026-11-17", ["2026-11-17"]),
])
def test_fines_de_mes_exactos_y_una_sola_consulta(inicio, fin, fechas):
    repo = Repositorio()
    respuesta = EvolucionBalanceService(repo).consultar(ConsultaEvolucionBalance(fecha_desde=inicio, fecha_hasta=fin, neteo=0))
    assert [c.fecha.isoformat() for c in respuesta.datos] == fechas
    assert repo.consultas == [dict(fechas=[date.fromisoformat(f) for f in fechas], id_agencia=1, id_empresa=1, codigos_cuenta=("1", "2", "3"))]
    assert respuesta.id_agencia == 0 and respuesta.id_agencia_contable == 1
    assert all(c.cuentas_sin_saldo == ["1", "2", "3"] for c in respuesta.datos)
    assert [c.parcial for c in respuesta.datos] == [f == "2026-11-17" for f in fechas]


def test_diario_inclusivo_con_ceros_ausencias_y_neteo_exacto():
    repo = Repositorio([
        fila("2026-10-30", "1", "100.01"), fila("2026-10-30", "1908", "0.02"),
        fila("2026-10-30", "2", "50.02"), fila("2026-10-30", "2908", "10.03"),
        fila("2026-10-30", "3", "0.00"), fila("2026-10-31", "1", "-1.23"),
        # Una cuenta hija no debe incorporarse al total padre.
        fila("2026-10-31", "11", "999.99"),
    ])
    consulta = ConsultaEvolucionBalance(frecuencia="diario", fecha_desde="2026-10-30", fecha_hasta="2026-11-01", id_agencia=2)
    respuesta = EvolucionBalanceService(repo).consultar(consulta)
    assert [c.fecha.isoformat() for c in respuesta.datos] == ["2026-10-30", "2026-10-31", "2026-11-01"]
    assert (respuesta.datos[0].activos, respuesta.datos[0].pasivos, respuesta.datos[0].patrimonio) == (Decimal("99.99"), Decimal("39.99"), Decimal("0.00"))
    assert respuesta.datos[1].activos == Decimal("-1.23")
    assert respuesta.datos[1].pasivos is None
    assert respuesta.datos[1].cuentas_sin_saldo == ["2", "3"]
    assert respuesta.datos[2].activos is None
    assert repo.consultas[0]["id_agencia"] == 2
    assert repo.consultas[0]["codigos_cuenta"] == ("1", "2", "3", "1908", "2908")
    sin_neteo = EvolucionBalanceService(repo).consultar(consulta.model_copy(update={"neteo": 0}))
    assert sin_neteo.datos[0].activos == Decimal("100.01")


def test_48_meses_y_un_ano_diario():
    mensual = ConsultaEvolucionBalance(fecha_desde="2022-11-01", fecha_hasta="2026-10-31")
    assert len(EvolucionBalanceService(Repositorio()).consultar(mensual).datos) == 48
    mensual_actual = ConsultaEvolucionBalance(fecha_desde="2022-12-01", fecha_hasta="2026-11-17")
    assert len(EvolucionBalanceService(Repositorio()).consultar(mensual_actual).datos) == 48
    diario = ConsultaEvolucionBalance(frecuencia="diario", fecha_desde="2025-11-18", fecha_hasta="2026-11-17")
    assert len(EvolucionBalanceService(Repositorio()).consultar(diario).datos) == 365
    # El límite se ajusta al último día del mes destino.
    ConsultaEvolucionBalance(frecuencia="diario", fecha_desde="2024-02-29", fecha_hasta="2025-02-27")
    with pytest.raises(ValidationError, match="un año"):
        ConsultaEvolucionBalance(frecuencia="diario", fecha_desde="2024-02-29", fecha_hasta="2025-02-28")


@pytest.mark.parametrize("cambios", [
    {"fecha_desde": "2022-10-01"},
    {"fecha_desde": "2026-11-01"},
    {"fecha_hasta": "2026-11-18"},
    {"fecha_hasta": "2026-02-30"},
    {"id_agencia": -1}, {"neteo": 2}, {"frecuencia": "anual"},
    {"frecuencia": "diario", "fecha_desde": "2025-10-31"},
])
def test_rechaza_rangos_y_parametros_invalidos(cambios):
    with pytest.raises(ValidationError):
        ConsultaEvolucionBalance(**{"fecha_desde": "2026-01-01", "fecha_hasta": "2026-10-31", **cambios})


def test_rango_sin_fin_de_mes():
    with pytest.raises(HTTPException) as exc:
        EvolucionBalanceService(Repositorio()).consultar(ConsultaEvolucionBalance(fecha_desde="2026-10-01", fecha_hasta="2026-10-15"))
    assert exc.value.status_code == 422


def test_endpoint_bearer_contrato_decimal_errores_y_agencia():
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    repo = Repositorio([fila("2026-10-31", "1", "100.01"), fila("2026-10-31", "3", "0.00")])
    app.dependency_overrides[get_evolucion_balance_service] = lambda: EvolucionBalanceService(repo)
    client = TestClient(app)
    url = "/analytic/evolucion-de-cuentas/evolucion-balance-general"
    body = {"fecha_desde": "2026-10-01", "fecha_hasta": "2026-10-31"}
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["nombre_agencia"] == "CONSOLIDADO"
    assert data["datos"] == [dict(fecha="2026-10-31", parcial=False, activos="100.01", pasivos=None, patrimonio="0.00", cuentas_sin_saldo=["2"])]
    actual = client.post(url, json={**body, "fecha_hasta": "2026-11-17"})
    assert actual.status_code == 200
    assert [(c["fecha"], c["parcial"]) for c in actual.json()["datos"]] == [("2026-10-31", False), ("2026-11-17", True)]
    assert client.post(url, json={**body, "id_agencia": 999}).status_code == 404
    assert client.post(url, json={**body, "fecha_hasta": "2026-11-18"}).status_code == 422
    assert client.post(url, json={**body, "frecuencia": "diario"}).status_code == 200


@pytest.mark.parametrize("hoy,esperado,parcial", [
    (date(2026, 11, 1), "2026-11-01", True),
    (date(2026, 11, 30), "2026-11-30", False),
    (date(2024, 2, 29), "2024-02-29", False),
])
def test_corte_actual_en_inicio_fin_de_mes_y_bisiesto(monkeypatch, hoy, esperado, parcial):
    monkeypatch.setattr(schemas, "fecha_actual_ecuador", lambda: hoy)
    consulta = ConsultaEvolucionBalance(fecha_desde=hoy.replace(day=1), fecha_hasta=hoy)
    respuesta = EvolucionBalanceService(Repositorio()).consultar(consulta)
    assert [(c.fecha.isoformat(), c.parcial) for c in respuesta.datos] == [(esperado, parcial)]
