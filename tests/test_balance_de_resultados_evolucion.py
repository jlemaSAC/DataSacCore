from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.analytic.evolucion_cuentas.balance_de_resultados.dependencies import (
    get_evolucion_resultados_service,
    get_variacion_resultados_service,
)
from app.modules.analytic.evolucion_cuentas.balance_de_resultados.service import (
    EvolucionResultadosService,
    VariacionResultadosService,
)
from app.modules.analytic.evolucion_cuentas.router import router
from app.modules.auth.dependencies import get_current_auth_context


class RepositorioResultados:
    def obtener_agencia(self, id_agencia):
        assert id_agencia == 1
        return {"nombre": "CONSOLIDADO", "id_empresa": 1}

    def obtener_saldos_fechas(self, *, fechas, id_agencia, id_empresa, codigos_cuenta):
        assert set(codigos_cuenta) == {"4", "5", "41019005", "51909005"}
        saldos = {
            date(2024, 1, 31): {"4": "30", "5": "60", "41019005": "1", "51909005": "2"},
            date(2024, 2, 29): {"4": "40", "5": "80", "41019005": "2", "51909005": "6"},
            date(2024, 3, 31): {"5": "90"},
        }
        return [
            {"fecha": fecha, "codigo_cuenta": codigo, "saldo": Decimal(saldo)}
            for fecha in fechas
            for codigo, saldo in saldos.get(fecha, {}).items()
        ]


@pytest.mark.parametrize(
    "operacion,parametros,esperado",
    [
        ("evolucion", {"frecuencia": "mensual"}, ("38", "74", "36")),
        ("variacion", {"tipo": "mensual_cortes"}, ("9", "16", "7")),
    ],
)
def test_resultados_por_endpoint(operacion, parametros, esperado):
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    repo = RepositorioResultados()
    app.dependency_overrides[get_evolucion_resultados_service] = lambda: EvolucionResultadosService(repo)
    app.dependency_overrides[get_variacion_resultados_service] = lambda: VariacionResultadosService(repo)
    client = TestClient(app)
    url = f"/analytic/evolucion-de-cuentas/{operacion}-balance-de-resultados"
    body = {"fecha_desde": "2024-02-01", "fecha_hasta": "2024-03-31", **parametros}
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    respuesta = client.post(url, json=body)
    assert respuesta.status_code == 200
    febrero, marzo = respuesta.json()["datos"]
    assert tuple(Decimal(febrero[indicador]) for indicador in ("gastos", "ingresos", "utilidad")) == tuple(map(Decimal, esperado))
    assert "activos" not in febrero
    assert marzo["gastos"] is None and marzo["utilidad"] is None
    assert marzo["cuentas_sin_saldo"] == ["4"]
    if operacion == "variacion":
        assert febrero["fecha_comparacion"] == "2024-01-31"
