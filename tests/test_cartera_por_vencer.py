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
        assert codigos_cuenta == ("14", "1499", "1402", "1403", "1404", "1401", "1410", "1418", "1412", "1420")
        saldos = {
            date(2024, 2, 29): {"14": 200, "1499": 10, "1402": 75, "1403": 20, "1401": 0, "1410": 5, "1418": 4, "1412": 3, "1420": 2},
            date(2024, 3, 31): {"14": 300, "1499": 25, "1402": 100, "1403": 18, "1404": 32, "1401": 0, "1410": 8, "1418": 6, "1412": 4, "1420": 1},
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
         EvolucionCarteraPorVencerService, (275, 100, 18, 32, 0, 8, 6, 4, 1)),
        ("historico", {"tipo": "mensual"}, get_historico_cartera_por_vencer_service,
         HistoricoCarteraPorVencerService, (85, 25, -2, None, 0, 3, 2, 1, -1)),
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
    if 'historico-' in url:
        nueva_ruta = url.replace('historico-', 'variacion-')
        assert cliente.post(nueva_ruta, json=body).json() == respuesta.json()
    assert respuesta.status_code == 200
    corte, = respuesta.json()["datos"]
    campos = ("cartera_total", "consumo", "inmobiliario", "microcredito", "productivo", "consumo_refinanciado", "consumo_reestructurado", "microcredito_refinanciado", "microcredito_reestructurado")
    assert tuple(Decimal(corte[campo]) if corte[campo] is not None else None for campo in campos) == esperado
    if operacion == "historico":
        assert corte["fecha_comparacion"] == "2024-02-29"
        assert corte["cuentas_sin_saldo"] == ["1404"]
