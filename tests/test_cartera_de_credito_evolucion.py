from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.analytic.evolucion_cuentas.cartera_de_credito.dependencies import (
    get_evolucion_cartera_service,
    get_historico_cartera_service,
)
from app.modules.analytic.evolucion_cuentas.cartera_de_credito.service import (
    EvolucionCarteraService,
    HistoricoCarteraService,
)
from app.modules.analytic.evolucion_cuentas.router import router
from app.modules.auth.dependencies import get_current_auth_context


class Repositorio:
    def obtener_agencia(self, id_agencia):
        assert id_agencia == 1
        return {"id_empresa": 1, "nombre": "CONSOLIDADO"}

    def obtener_saldos_fechas(self, *, fechas, id_agencia, id_empresa, codigos_cuenta):
        saldos = {
            date(2024, 2, 29): {"14": 200, "1499": -10, "1402": 9, "1403": 3, "1401": 0},
            date(2024, 3, 31): {
                "14": 300,
                "1499": -25,
                "1408": 30, "1410": 20, "1450": 4, "149910": -5,
                "1419": 8, "149915": -2,
                "1428": 35, "149920": -1,
                "1401": 0,
            },
        }
        assert len(codigos_cuenta) == len(set(codigos_cuenta))
        assert "1499" in codigos_cuenta
        return [
            {"fecha": fecha, "codigo_cuenta": codigo, "saldo": Decimal(importe)}
            for fecha in fechas
            for codigo, importe in saldos.get(fecha, {}).items()
            if codigo in codigos_cuenta
        ]


@pytest.mark.parametrize(
    "ruta,modo,esperado",
    [
        ("evolucion", {"frecuencia": "mensual"}, (325, 54, 8, 35, 0)),
        ("historico", {"tipo": "mensual"}, (115, 45, 5, None, 0)),
    ],
)
def test_endpoints_cartera(ruta, modo, esperado):
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    app.dependency_overrides[get_evolucion_cartera_service] = lambda: EvolucionCarteraService(Repositorio())
    app.dependency_overrides[get_historico_cartera_service] = lambda: HistoricoCarteraService(Repositorio())
    cliente = TestClient(app)
    url = f"/analytic/evolucion-de-cuentas/{ruta}-cartera-de-credito"
    body = {"fecha_desde": "2024-03-31", "fecha_hasta": "2024-03-31", **modo}
    assert cliente.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    respuesta = cliente.post(url, json=body)
    if 'historico-' in url:
        nueva_ruta = url.replace('historico-', 'variacion-')
        assert cliente.post(nueva_ruta, json=body).json() == respuesta.json()
    assert respuesta.status_code == 200
    corte, = respuesta.json()["datos"]
    claves = ("cartera_total", "consumo", "inmobiliario", "microcredito", "productivo")
    assert tuple(Decimal(corte[campo]) if corte[campo] is not None else None for campo in claves) == esperado
    if ruta == "historico":
        assert corte["fecha_comparacion"] == "2024-02-29"
        assert corte["cuentas_sin_saldo"] == ["microcredito"]


def test_cartera_total_sin_ajuste_o_sin_cuenta_principal():
    servicio = EvolucionCarteraService(Repositorio())
    fecha = date(2024, 3, 31)
    assert servicio.valores_corte({(fecha, "14"): Decimal("100")}, fecha, {})["cartera_total"] == 100
    assert servicio.valores_corte({(fecha, "14"): Decimal("100"), (fecha, "1499"): Decimal("20")}, fecha, {})["cartera_total"] == 80
    assert servicio.valores_corte({(fecha, "1499"): Decimal("20")}, fecha, {})["cartera_total"] is None
