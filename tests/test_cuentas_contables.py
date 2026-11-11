from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.analytic.analisis_contable.router import router
from app.modules.analytic.analisis_contable.cuentas_contables.dependencies import get_cuentas_contables_service
from app.modules.analytic.analisis_contable.cuentas_contables.schemas import ConsultaCuentasContables
from app.modules.analytic.analisis_contable.cuentas_contables.service import CUENTAS, CuentasContablesService


class Repositorio:
    def __init__(self, saldos=None):
        self.saldos = {
            "1": Decimal("300000000.01"), "14": Decimal("142449311.65"),
            "1499": Decimal("-13766476.35"), "13": Decimal("10879461.68"),
            "2": Decimal("281426967.95"), "2101": Decimal("28762353.03"),
            "2103": Decimal("143408937.89"), "3": Decimal("18208633.96"),
            "31": Decimal("6995210.19"), "33": Decimal("11213423.77"),
        } if saldos is None else saldos
        self.argumentos = None

    def obtener_agencia(self, id_agencia):
        return {"nombre": "CONSOLIDADO" if id_agencia == 1 else "MATRIZ", "id_empresa": 1} if id_agencia in (1, 2) else None

    def obtener_saldos(self, **kwargs):
        self.argumentos = kwargs
        return self.saldos


def test_diez_formulas_y_consolidado_sin_duplicar_agencias_o_cuentas_hijas():
    repo = Repositorio()
    respuesta = CuentasContablesService(repo).consultar(ConsultaCuentasContables(fecha_corte="2026-11-10", neteo=0))
    assert respuesta.id_agencia == 0
    assert respuesta.id_agencia_contable == 1
    assert respuesta.nombre_agencia == "CONSOLIDADO"
    assert respuesta.cuentas_sin_saldo == []
    assert repo.argumentos == dict(fecha_corte=date(2026, 11, 10), id_agencia=1, id_empresa=1, codigos_cuenta=CUENTAS)
    assert len(CUENTAS) == len(set(CUENTAS)) == 10
    assert [item.saldo for item in respuesta.indicadores] == [
        Decimal("300000000.01"), Decimal("156215788.00"), Decimal("142449311.65"),
        Decimal("10879461.68"), Decimal("281426967.95"), Decimal("28762353.03"),
        Decimal("143408937.89"), Decimal("18208633.96"), Decimal("6995210.19"), Decimal("11213423.77"),
    ]


@pytest.mark.parametrize("provision, esperado", [("10.01", "89.99"), ("-10.01", "110.01"), ("0.00", "100.00")])
def test_cartera_bruta_resta_saldo_con_su_signo(provision, esperado):
    repo = Repositorio({"14": Decimal("100.00"), "1499": Decimal(provision)})
    respuesta = CuentasContablesService(repo).consultar(ConsultaCuentasContables(fecha_corte="2026-11-10", id_agencia=2))
    assert respuesta.indicadores[1].saldo == Decimal(esperado)
    assert repo.argumentos["id_agencia"] == 2


def test_cero_es_valido_y_ausencia_no_se_convierte_a_cero():
    repo = Repositorio({"14": Decimal("0.00"), "1": Decimal("0.00")})
    respuesta = CuentasContablesService(repo).consultar(ConsultaCuentasContables(fecha_corte="2026-11-10"))
    assert respuesta.indicadores[0].saldo == Decimal("0.00")
    assert respuesta.indicadores[1].saldo is None  # falta 1499 para calcular cartera bruta
    assert respuesta.indicadores[2].saldo == Decimal("0.00")
    assert "1499" in respuesta.cuentas_sin_saldo
    assert "14" not in respuesta.cuentas_sin_saldo
    vacio = CuentasContablesService(Repositorio({})).consultar(ConsultaCuentasContables(fecha_corte="2026-11-10"))
    assert len(vacio.cuentas_sin_saldo) == 10
    assert all(indicador.saldo is None for indicador in vacio.indicadores)


def test_endpoint_autenticacion_contrato_validacion_y_agencia_inexistente():
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    app.dependency_overrides[get_cuentas_contables_service] = lambda: CuentasContablesService(Repositorio())
    client = TestClient(app)
    url = "/analytic/analisis-contable/cuentas-contables"
    body = {"fecha_corte": "2026-11-10", "id_agencia": 2}
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json=body)
    assert response.status_code == 200
    datos = response.json()
    assert datos["fecha_corte"] == "2026-11-10"
    assert datos["id_agencia_contable"] == 2
    assert datos["nombre_agencia"] == "MATRIZ"
    assert datos["neteo"] == 1
    assert datos["indicadores"][1] == {
        "codigo": "cartera_bruta", "nombre": "Cartera Bruta", "formula": "14 - 1499", "saldo": "156215788.00",
    }
    assert datos["indicadores"][0]["formula"] == "1 - 1908"
    sin_neteo = client.post(url, json={**body, "neteo": 0}).json()
    assert sin_neteo["neteo"] == 0
    assert sin_neteo["indicadores"][0]["formula"] == "1"
    assert client.post(url, json={**body, "fecha_corte": "2026-02-30"}).status_code == 422
    assert client.post(url, json={**body, "id_agencia": -1}).status_code == 422
    assert client.post(url, json={**body, "neteo": 2}).status_code == 422
    assert client.post(url, json={"id_agencia": 0}).status_code == 422
    assert client.post(url, json={**body, "id_agencia": 999999}).status_code == 404
    app.dependency_overrides[get_cuentas_contables_service] = lambda: CuentasContablesService(Repositorio({}))
    datos = client.post(url, json=body).json()
    assert len(datos["indicadores"]) == 10
    assert all(item["saldo"] is None for item in datos["indicadores"])


@pytest.mark.parametrize("neteo", [0, 1])
def test_neteo_coincide_con_cuentas_contables(neteo):
    from app.modules.contabilidad.saldos_diarios.schemas import ConsultaSaldosDiarios
    from app.modules.contabilidad.saldos_diarios.service import SaldosDiariosService

    repo = Repositorio()
    repo.saldos.update({"1908": Decimal("1000000.01"), "2908": Decimal("250000.02")})
    resumen = CuentasContablesService(repo).consultar(
        ConsultaCuentasContables(fecha_corte="2026-11-10", neteo=neteo)
    )
    assert resumen.neteo == neteo
    assert set(repo.argumentos["codigos_cuenta"]) == set(CUENTAS) | ({"1908", "2908"} if neteo else set())

    class RepositorioDiario:
        def obtener_empresa_agencia(self, id_agencia):
            return 1

        def obtener_cuentas_activas(self, empresa):
            return [{"codigo_cuenta": cuenta, "nombre_cuenta": cuenta} for cuenta in CUENTAS]

        def obtener_saldos(self, **kwargs):
            return [{"fecha": date(2026, 11, 10), "codigo_cuenta": cuenta, "saldo": saldo}
                    for cuenta, saldo in repo.saldos.items()]

    diario = SaldosDiariosService(RepositorioDiario()).consultar(ConsultaSaldosDiarios(
        fecha_desde="2026-11-10", fecha_hasta="2026-11-10", id_agencia=0, neteo=neteo,
    ))
    saldos = {item.codigo_cuenta: item.saldo for item in diario.datos}
    assert resumen.indicadores[0].saldo == saldos["1"]
    assert resumen.indicadores[4].saldo == saldos["2"]
    assert resumen.indicadores[0].formula == ("1 - 1908" if neteo else "1")
    assert resumen.indicadores[4].formula == ("2 - 2908" if neteo else "2")
    assert resumen.indicadores[1].saldo == saldos["14"] - saldos["1499"]
    assert resumen.indicadores[0].saldo == Decimal("300000000.01") - (Decimal("1000000.01") if neteo else 0)
    assert resumen.indicadores[4].saldo == Decimal("281426967.95") - (Decimal("250000.02") if neteo else 0)


def test_neteo_conserva_cero_y_no_inventa_saldo_para_cuenta_base_ausente():
    repo = Repositorio({"1": Decimal("10.01"), "1908": Decimal("10.01"), "2908": Decimal("5.00")})
    respuesta = CuentasContablesService(repo).consultar(ConsultaCuentasContables(fecha_corte="2026-11-10"))
    assert respuesta.indicadores[0].saldo == Decimal("0.00")
    assert respuesta.indicadores[4].saldo is None
    assert "2" in respuesta.cuentas_sin_saldo
    assert "1" not in respuesta.cuentas_sin_saldo
