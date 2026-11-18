from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.analytic.evolucion_cuentas.depositos_a_plazos.dependencies import (
    get_evolucion_depositos_a_plazos_service,
    get_variacion_depositos_a_plazos_service,
)
from app.modules.analytic.evolucion_cuentas.depositos_a_plazos.service import (
    EvolucionDepositosAPlazosService,
    VariacionDepositosAPlazosService,
)
from app.modules.analytic.evolucion_cuentas.router import router
from app.modules.auth.dependencies import get_current_auth_context


class Repositorio:
    def obtener_agencia(self, id_agencia):
        assert id_agencia == 1
        return {"id_empresa": 1, "nombre": "CONSOLIDADO"}

    def obtener_saldos_fechas(self, *, fechas, id_agencia, id_empresa, codigos_cuenta):
        assert codigos_cuenta[:5] == ("210305", "210310", "210315", "210320", "210325")
        saldos = {
            date(2024, 2, 29): dict(zip(codigos_cuenta, (75, 20, 0, 40, 30, 200))),
            date(2024, 3, 31): dict(zip(codigos_cuenta, (100, 0, 0, 32, 45, 250))),
        }
        return [
            {"fecha": fecha, "codigo_cuenta": codigo, "saldo": Decimal(importe)}
            for fecha in fechas
            for codigo, importe in saldos.get(fecha, {}).items()
        ]


@pytest.mark.parametrize(
    "operacion,consulta,dependencia,servicio,esperado",
    [
        ("evolucion", {"frecuencia": "mensual"}, get_evolucion_depositos_a_plazos_service,
         EvolucionDepositosAPlazosService, (100, 0, 0, 32, 45)),
        ("variacion", {"tipo": "mensual"}, get_variacion_depositos_a_plazos_service,
         VariacionDepositosAPlazosService, (25, -20, 0, -8, 15)),
    ],
)
def test_consulta_depositos_plazos(operacion, consulta, dependencia, servicio, esperado):
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    app.dependency_overrides[dependencia] = lambda: servicio(Repositorio())
    cliente = TestClient(app)
    url = f"/analytic/evolucion-de-cuentas/{operacion}-depositos-a-plazos"
    body = {"fecha_desde": "2024-03-31", "fecha_hasta": "2024-03-31", **consulta}
    assert cliente.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    respuesta = cliente.post(url, json=body)
    assert respuesta.status_code == 200
    corte, = respuesta.json()["datos"]
    campos = ("plazo_1_30", "plazo_31_90", "plazo_91_180", "plazo_181_360", "plazo_mas_361")
    assert tuple(Decimal(corte[campo]) for campo in campos) == esperado
    assert corte["cuentas_sin_saldo"] == []
    if operacion == "evolucion":
        assert Decimal(corte["depositos_plazo"]) == 250
    else:
        assert "depositos_plazo" not in corte
    vacio = cliente.post(url, json={**body, "fecha_desde": "2024-04-30", "fecha_hasta": "2024-04-30"})
    assert vacio.status_code == 200
    assert all(vacio.json()["datos"][0][campo] is None for campo in campos)
