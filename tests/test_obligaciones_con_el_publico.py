from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.analytic.evolucion_cuentas.obligaciones_con_el_publico.dependencies import (
    get_evolucion_obligaciones_con_el_publico_service,
    get_historico_obligaciones_con_el_publico_service,
)
from app.modules.analytic.evolucion_cuentas.obligaciones_con_el_publico.service import (
    EvolucionObligacionesConElPublicoService,
    HistoricoObligacionesConElPublicoService,
)
from app.modules.analytic.evolucion_cuentas.router import router
from app.modules.auth.dependencies import get_current_auth_context


class Repositorio:
    def obtener_agencia(self, id_agencia):
        assert id_agencia == 1
        return {"id_empresa": 1, "nombre": "CONSOLIDADO"}

    def obtener_saldos_fechas(self, *, fechas, id_agencia, id_empresa, codigos_cuenta):
        assert codigos_cuenta == ("2103", "2101", "2105")
        saldos = {
            date(2024, 2, 29): {"2103": 75, "2101": 20},
            date(2024, 3, 31): {"2103": 100, "2101": 0, "2105": 32},
        }
        return [
            {"fecha": fecha, "codigo_cuenta": codigo, "saldo": Decimal(importe)}
            for fecha in fechas
            for codigo, importe in saldos.get(fecha, {}).items()
        ]


@pytest.mark.parametrize(
    "operacion,consulta,dependencia,servicio,esperado",
    [
        ("evolucion", {"frecuencia": "mensual"}, get_evolucion_obligaciones_con_el_publico_service,
         EvolucionObligacionesConElPublicoService, (100, 0, 32)),
        ("historico", {"tipo": "mensual"}, get_historico_obligaciones_con_el_publico_service,
         HistoricoObligacionesConElPublicoService, (25, -20, None)),
    ],
)
def test_consulta_obligaciones_con_el_publico(operacion, consulta, dependencia, servicio, esperado):
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    app.dependency_overrides[dependencia] = lambda: servicio(Repositorio())
    cliente = TestClient(app)
    url = f"/analytic/evolucion-de-cuentas/{operacion}-obligaciones-con-el-publico"
    body = {"fecha_desde": "2024-03-31", "fecha_hasta": "2024-03-31", **consulta}
    assert cliente.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    respuesta = cliente.post(url, json=body)
    assert respuesta.status_code == 200
    corte, = respuesta.json()["datos"]
    campos = ("depositos_plazo", "depositos_vista", "depositos_restringidos")
    assert tuple(Decimal(corte[campo]) if corte[campo] is not None else None for campo in campos) == esperado
    if operacion == "historico":
        assert corte["fecha_comparacion"] == "2024-02-29"
        assert corte["cuentas_sin_saldo"] == ["2105"]
