from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.analytic.evolucion_cuentas.cartera_no_devenga.dependencies import (
    get_evolucion_cartera_no_devenga_service, get_historico_cartera_no_devenga_service,
)
from app.modules.analytic.evolucion_cuentas.cartera_no_devenga.service import (
    EvolucionCarteraNoDevengaService, HistoricoCarteraNoDevengaService,
)
from app.modules.analytic.evolucion_cuentas.router import router
from app.modules.auth.dependencies import get_current_auth_context


class Repositorio:
    def obtener_agencia(self, id_agencia):
        return {"id_empresa": 1, "nombre": "CONSOLIDADO"}

    def obtener_saldos_fechas(self, *, fechas, id_agencia, id_empresa, codigos_cuenta):
        assert codigos_cuenta == ("14", "1499", "1426", "1434", "1442", "1427", "1428", "1436", "1444")
        valores = {date(2024, 2, 29): (100, 10, 1, 2, 3, 4, 5, 6, 7), date(2024, 3, 31): (200, 20, 2, 4, 6, 8, 10, 12, 14)}
        return [{"fecha": f, "codigo_cuenta": c, "saldo": Decimal(v)} for f in fechas for c, v in zip(codigos_cuenta, valores.get(f, ()))]


@pytest.mark.parametrize("operacion,consulta,dependencia,servicio,esperado", [
    ("evolucion", {"frecuencia": "mensual"}, get_evolucion_cartera_no_devenga_service, EvolucionCarteraNoDevengaService, (180, 2, 4, 6, 8, 10, 12, 14)),
    ("variacion", {"tipo": "mensual"}, get_historico_cartera_no_devenga_service, HistoricoCarteraNoDevengaService, (90, 1, 2, 3, 4, 5, 6, 7)),
])
def test_cartera_no_devenga(operacion, consulta, dependencia, servicio, esperado):
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    app.dependency_overrides[dependencia] = lambda: servicio(Repositorio())
    cliente = TestClient(app)
    url = f"/analytic/evolucion-de-cuentas/{operacion}-cartera-no-devenga"
    body = {"fecha_desde": "2024-03-31", "fecha_hasta": "2024-03-31", **consulta}
    assert cliente.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    respuesta = cliente.post(url, json=body)
    assert respuesta.status_code == 200
    corte = respuesta.json()["datos"][0]
    campos = ("cartera_total", "consumo", "consumo_refinanciado", "consumo_reestructurado", "inmobiliario", "microcredito", "microcredito_refinanciado", "microcredito_reestructurado")
    assert tuple(Decimal(corte[campo]) for campo in campos) == esperado
