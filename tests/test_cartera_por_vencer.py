from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.analytic.evolucion_cuentas.cartera_por_vencer.dependencies import (
    get_evolucion_cartera_por_vencer_service,
    get_historico_cartera_por_vencer_service,
)
from app.modules.analytic.evolucion_cuentas.cartera_por_vencer.service import (
    EvolucionCarteraPorVencerService,
    HistoricoCarteraPorVencerService,
)
from app.modules.analytic.evolucion_cuentas.router import router
from app.modules.auth.dependencies import get_current_auth_context


class Repositorio:
    def obtener_agencia(self, id_agencia):
        assert id_agencia == 1
        return {"id_empresa": 1, "nombre": "CONSOLIDADO"}

    def obtener_saldos_fechas(self, *, fechas, id_agencia, id_empresa, codigos_cuenta):
        assert codigos_cuenta == ("1402", "1403", "1404", "1401")
        saldos = {
            date(2024, 2, 29): {"1402": 75, "1403": 20, "1401": 0},
            date(2024, 3, 31): {"1402": 100, "1403": 18, "1404": 32, "1401": 0},
        }
        return [
            {"fecha": fecha, "codigo_cuenta": codigo, "saldo": Decimal(importe)}
            for fecha in fechas
            for codigo, importe in saldos.get(fecha, {}).items()
        ]


@pytest.mark.parametrize(
    "operacion,consulta,dependencia,servicio,esperado",
    [
        ("evolucion", {"frecuencia": "mensual"}, get_evolucion_cartera_por_vencer_service,
         EvolucionCarteraPorVencerService, (100, 18, 32, 0)),
        ("historico", {"tipo": "mensual"}, get_historico_cartera_por_vencer_service,
         HistoricoCarteraPorVencerService, (25, -2, None, 0)),
    ],
)
def test_consulta_cartera_por_vencer(operacion, consulta, dependencia, servicio, esperado):
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    app.dependency_overrides[dependencia] = lambda: servicio(Repositorio())
    cliente = TestClient(app)
    url = f"/analytic/evolucion-de-cuentas/{operacion}-cartera-por-vencer"
    body = {"fecha_desde": "2024-03-31", "fecha_hasta": "2024-03-31", **consulta}
    assert cliente.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    respuesta = cliente.post(url, json=body)
    assert respuesta.status_code == 200
    corte, = respuesta.json()["datos"]
    campos = ("consumo", "inmobiliario", "microcredito", "productivo")
    assert tuple(Decimal(corte[campo]) if corte[campo] is not None else None for campo in campos) == esperado
    assert "cartera_total" not in corte
    if operacion == "historico":
        assert corte["fecha_comparacion"] == "2024-02-29"
        assert corte["cuentas_sin_saldo"] == ["1404"]
