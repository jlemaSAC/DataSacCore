from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.analytic.analisis_contable.router import router
from app.modules.analytic.analisis_contable.resumen_balance_de_resultados.dependencies import get_balance_resultados_service
from app.modules.analytic.analisis_contable.resumen_balance_de_resultados.schemas import ConsultaBalanceResultados
from app.modules.analytic.analisis_contable.resumen_balance_de_resultados.service import BalanceResultadosService, CUENTAS
from app.modules.contabilidad.saldos_diarios.schemas import ConsultaSaldosDiarios
from app.modules.contabilidad.saldos_diarios.service import SaldosDiariosService


class Repositorio:
    def __init__(self, saldos=None):
        self.saldos = {cuenta: Decimal(saldo) for cuenta, saldo in {
            "4": "1000.00", "41": "100.00", "44": "50.00", "45": "200.00",
            "5": "1400.00", "51": "700.00", "52": "30.00", "53": "20.00",
            "54": "60.00", "42": "10.00", "43": "5.00",
            "41019005": "25.00", "51909005": "40.00",
            "1": "5000.00", "2": "3000.00", "3": "1600.00",
        }.items()} if saldos is None else saldos
        self.argumentos = None

    def obtener_agencia(self, id_agencia):
        return {"nombre": "CONSOLIDADO" if id_agencia == 1 else "MATRIZ", "id_empresa": 1} if id_agencia in (1, 2) else None

    def obtener_saldos(self, **kwargs):
        self.argumentos = kwargs
        return self.saldos


def consultar(repo=None, neteo=0, id_agencia=0):
    return BalanceResultadosService(repo or Repositorio()).consultar(ConsultaBalanceResultados(
        fecha_corte="2026-11-10", id_agencia=id_agencia, neteo=neteo,
    ))


def test_diez_indicadores_y_desglose_completo_de_margenes():
    repo = Repositorio()
    respuesta = consultar(repo)
    assert [item.codigo for item in respuesta.indicadores] == [
        "gastos", "intereses_causados", "provisiones", "gasto_operativo", "ingresos",
        "intereses_ganados", "comisiones_ganadas", "utilidades_financieras", "margen_intermediacion", "utilidad",
    ]
    assert [item.saldo for item in respuesta.indicadores] == list(map(Decimal, [
        "1000.00", "100.00", "50.00", "200.00", "1400.00", "700.00", "30.00", "20.00", "445.00", "400.00",
    ]))
    assert [item.saldo for item in respuesta.margenes] == list(map(Decimal, ["600.00", "695.00", "645.00", "445.00"]))
    assert respuesta.margenes[-1].formula == "51 - 41 + 52 + 54 - 42 + 53 - 43 - 44 - 45"
    assert respuesta.cuentas_sin_saldo == []
    assert repo.argumentos["fecha_corte"] == date(2026, 11, 10)
    assert repo.argumentos["id_agencia"] == respuesta.id_agencia_contable == 1
    assert len(set(repo.argumentos["codigos_cuenta"])) == len(repo.argumentos["codigos_cuenta"])
    assert not {"41019005", "51909005"} & set(repo.argumentos["codigos_cuenta"])


@pytest.mark.parametrize("neteo", [0, 1])
def test_neteo_de_cuentas_y_margenes_coincide_con_saldos_diarios(neteo):
    repo = Repositorio()
    respuesta = consultar(repo, neteo=neteo, id_agencia=2)

    class RepositorioDiario:
        def obtener_empresa_agencia(self, agencia):
            return 1

        def obtener_cuentas_activas(self, empresa):
            return [{"codigo_cuenta": cuenta, "nombre_cuenta": cuenta} for cuenta in CUENTAS]

        def obtener_saldos(self, **kwargs):
            return [{"fecha": date(2026, 11, 10), "codigo_cuenta": cuenta, "saldo": saldo}
                    for cuenta, saldo in repo.saldos.items()]

    diario = SaldosDiariosService(RepositorioDiario()).consultar(ConsultaSaldosDiarios(
        fecha_desde="2026-11-10", fecha_hasta="2026-11-10", id_agencia=2, neteo=neteo,
    ))
    saldos = {item.codigo_cuenta: item.saldo for item in diario.datos}
    for indicador, cuenta in zip(respuesta.indicadores[:8], ("4", "41", "44", "45", "5", "51", "52", "53")):
        assert indicador.saldo == saldos[cuenta]
    assert respuesta.indicadores[-1].saldo == saldos["5"] - saldos["4"]
    assert respuesta.indicadores[-2].saldo == (saldos["51"] - saldos["41"] + saldos["52"] + saldos["54"]
                                             - saldos["42"] + saldos["53"] - saldos["43"] - saldos["44"] - saldos["45"])
    assert respuesta.indicadores[-1].saldo == Decimal("385.00" if neteo else "400.00")
    assert respuesta.indicadores[-2].saldo == Decimal("430.00" if neteo else "445.00")
    assert respuesta.indicadores[-1].formula == ("(5 - 51909005) - (4 - 41019005)" if neteo else "5 - 4")
    assert respuesta.id_agencia_contable == repo.argumentos["id_agencia"] == 2
    assert respuesta.validacion_utilidad.estado == "coincide"
    assert respuesta.validacion_utilidad.utilidad_sin_neteo == Decimal("400.00")
    assert respuesta.validacion_utilidad.ajuste_neteo == Decimal("-15.00" if neteo else "0.00")


def test_cuenta_faltante_no_inventa_ceros_y_solo_afecta_indicadores_dependientes():
    repo = Repositorio()
    del repo.saldos["54"]
    respuesta = consultar(repo)
    assert respuesta.cuentas_sin_saldo == ["54"]
    assert respuesta.indicadores[-2].saldo is None
    assert respuesta.indicadores[-1].saldo == Decimal("400.00")
    assert respuesta.margenes[0].saldo == Decimal("600.00")
    assert all(item.saldo is None for item in respuesta.margenes[1:])


def test_conserva_ceros_perdidas_y_ajustes_ausentes():
    repo = Repositorio()
    repo.saldos["4"] = Decimal("1500.01")
    repo.saldos["5"] = Decimal("1400.00")
    repo.saldos["52"] = Decimal("0.00")
    del repo.saldos["41019005"]
    del repo.saldos["51909005"]
    respuesta = consultar(repo, neteo=1)
    assert respuesta.indicadores[-1].saldo == Decimal("-100.01")
    assert respuesta.indicadores[6].saldo == Decimal("0.00")
    assert respuesta.cuentas_sin_saldo == []
    assert respuesta.validacion_utilidad.ajuste_neteo == Decimal("0.00")


def test_validacion_detecta_un_centavo_sin_reemplazar_utilidad():
    repo = Repositorio()
    repo.saldos["1"] += Decimal("0.01")
    respuesta = consultar(repo)
    assert respuesta.validacion_utilidad.estado == "diferencia"
    assert respuesta.validacion_utilidad.resultado_contable == Decimal("400.01")
    assert respuesta.validacion_utilidad.diferencia == Decimal("-0.01")
    assert respuesta.indicadores[-1].saldo == Decimal("400.00")


def test_validacion_sin_saldos_no_bloquea_indicadores_y_vacio_se_conserva():
    repo = Repositorio()
    del repo.saldos["3"]
    respuesta = consultar(repo)
    assert respuesta.validacion_utilidad.estado == "sin_datos"
    assert respuesta.validacion_utilidad.cuentas_sin_saldo == ["3"]
    assert respuesta.validacion_utilidad.diferencia is None
    assert respuesta.cuentas_sin_saldo == []
    assert respuesta.indicadores[-1].saldo == Decimal("400.00")
    vacio = consultar(Repositorio({}))
    assert all(item.saldo is None for item in (*vacio.indicadores, *vacio.margenes))
    assert set(vacio.cuentas_sin_saldo) == set(CUENTAS)
    assert vacio.validacion_utilidad.estado == "sin_datos"


def test_endpoint_autenticacion_validacion_serializacion_y_agencias():
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    app.dependency_overrides[get_balance_resultados_service] = lambda: BalanceResultadosService(Repositorio())
    client = TestClient(app)
    url = "/analytic/analisis-contable/resumen-balance-de-resultados"
    body = {"fecha_corte": "2026-11-10"}
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json=body)
    assert response.status_code == 200
    datos = response.json()
    assert datos["id_agencia"] == 0 and datos["id_agencia_contable"] == 1 and datos["neteo"] == 1
    assert datos["indicadores"][-1]["saldo"] == "385.00"
    assert datos["margenes"][-1]["saldo"] == "430.00"
    assert datos["validacion_utilidad"]["diferencia"] == "0.00"
    assert client.post(url, json={**body, "neteo": 0}).json()["indicadores"][-1]["saldo"] == "400.00"
    assert client.post(url, json={**body, "id_agencia": 2}).json()["id_agencia_contable"] == 2
    assert client.post(url, json={**body, "id_agencia": 999999}).status_code == 404
    for invalido in ({}, {**body, "neteo": 2}, {**body, "id_agencia": -1}, {**body, "fecha_corte": "2026-02-30"}):
        assert client.post(url, json=invalido).status_code == 422
