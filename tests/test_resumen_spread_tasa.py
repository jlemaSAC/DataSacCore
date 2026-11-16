from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.modules.analytic.spread_tasa.resumen_spread_tasa.dependencies import get_resumen_spread_tasa_service
from app.modules.analytic.spread_tasa.resumen_spread_tasa.router import router
from app.modules.analytic.spread_tasa.resumen_spread_tasa.service import CUENTAS_PROMEDIO, ResumenSpreadTasaService
from app.modules.auth.dependencies import get_current_auth_context


class Repo:
    def __init__(self, id_agencia=1):
        self.id_agencia = id_agencia

    def get_saldos_contables_con_neteo(self, **kwargs):
        assert kwargs['id_agencia'] == self.id_agencia and kwargs['preservar_decimal']
        assert '41' in kwargs['codigos_cuenta'] and '4101' not in kwargs['codigos_cuenta']
        return [{'CodigoCuenta': c, 'SaldoFinal': Decimal(v)} for c, v in {
            '410130': '10', '410115': '4', '4103': '2', '41': '24',
            '510420': '30', '510410': '10', '510415': '3', '510430': '5',
        }.items()]

    def get_saldos_contables_fechas_con_neteo(self, **kwargs):
        assert kwargs['id_agencia'] == self.id_agencia and kwargs['preservar_decimal']
        assert kwargs['fechas'][0] == datetime(2025, 12, 31)
        assert set(kwargs['codigos_cuenta']) == {
            '2103', '2101', '26', '21', '210105', '210115', '210135', '210145',
            '2102', '2104', '2105', '22', '2601', '2602', '2603', '2604',
            '2606', '2607', '2609', '2610', '2690', '27', '1401', '1402', '1403', '1404', '1405',
            '1406', '1407', '1408', '1409', '1410', '1411', '1412', '1416',
            '1417', '1418', '1419', '1420', '1424', '1473', '1475', '1477',
        }
        return [{'Fecha': fecha, 'CodigoCuenta': c, 'SaldoFinal': Decimal(v)}
                for fecha in [datetime(2025, 12, 31), datetime(2026, 2, 2)]
                for c, v in {'2103': '100', '2101': '40', '26': '20', '21': '200',
                             '1404': '100', '1402': '50',
                             '1412': '30', '1420': '20', '1401': '10', '1403': '15', '1473': '25',
                             **{codigo: '2' for codigo in ('210105', '210115', '210135', '210145',
                                 '2102', '2104', '2105', '22', '2601', '2602', '2603', '2604',
                                 '2606', '2607', '2609', '2610', '2690', '27')},
                             **{codigo: '1' for codigo in ('1405', '1406', '1407', '1408', '1409',
                                 '1410', '1411', '1416', '1417', '1418', '1419', '1424', '1475', '1477')}}.items()]


def test_calculos_y_fondeos_distintos():
    result = ResumenSpreadTasaService(Repo()).consultar(date(2026, 2, 2))
    i = result.indicadores
    assert i.costo_ahorro_plazo == pytest.approx(.6)
    assert i.costo_ahorro_vista == pytest.approx(.6)
    assert i.costo_obligaciones_financieras == pytest.approx(2 / 20 * 6)
    assert result.saldos_promedio['fuentes_fondeo'] == 136
    assert i.costo_promedio_fondeo == pytest.approx(24 / 136 * 6)
    assert result.costo_fuentes_fondeo_spread == pytest.approx(24 / 136 * 6)
    assert i.rendimiento_cartera_por_vencer == pytest.approx(48 / 264 * 6)
    assert i.inmobiliario_por_vencer == pytest.approx(3 / 15 * 6)
    assert i.rendimiento_microcredito_por_vencer == pytest.approx(30 / 150 * 6)
    assert i.spread_tasa == pytest.approx(48 / 264 * 6 - 24 / 136 * 6)
    assert result.saldos_promedio['cartera_por_vencer'] == 264
    assert i.rendimiento_credito_consumo_por_vencer == pytest.approx(10 / 50 * 6)
    assert result.dias_con_datos == 2


def test_promedio_incluye_cierre_de_diciembre():
    class ConDiciembre(Repo):
        def get_saldos_contables_fechas_con_neteo(self, **kwargs):
            assert kwargs['fechas'][0] == datetime(2025, 12, 31)
            return [
                {'Fecha': datetime(2025, 12, 31), 'CodigoCuenta': '2103', 'SaldoFinal': Decimal('200')},
                {'Fecha': datetime(2026, 2, 2), 'CodigoCuenta': '2103', 'SaldoFinal': Decimal('100')},
            ]
    result = ResumenSpreadTasaService(ConDiciembre()).consultar(date(2026, 2, 2))
    assert result.fecha_promedio_desde == date(2025, 12, 31)
    assert result.saldos_promedio['2103'] == 150
    assert result.indicadores.costo_ahorro_plazo == pytest.approx(0.4)


def test_solicita_solo_cierres_y_fecha_de_corte():
    class VerificarFechas(Repo):
        def get_saldos_contables_fechas_con_neteo(self, **kwargs):
            assert kwargs['fechas'] == [
                datetime(2025, 12, 31), datetime(2026, 1, 31),
                datetime(2026, 2, 28), datetime(2026, 3, 15),
            ]
            return [
                {'Fecha': fecha, 'CodigoCuenta': '2103', 'SaldoFinal': Decimal(valor)}
                for fecha, valor in zip(kwargs['fechas'], ('100', '200', '300', '400'))
            ]
    resultado = ResumenSpreadTasaService(VerificarFechas()).consultar(date(2026, 3, 15))
    assert resultado.saldos_promedio['2103'] == 250
    assert resultado.dias_con_datos == 4
    assert resultado.indicadores.costo_ahorro_plazo == pytest.approx(10 / 250 * 4)


def test_corte_en_fin_de_mes_no_se_duplica():
    class VerificarFechas(Repo):
        def get_saldos_contables_fechas_con_neteo(self, **kwargs):
            assert kwargs['fechas'] == [datetime(2025, 12, 31), datetime(2026, 1, 31)]
            return [{'Fecha': fecha, 'CodigoCuenta': '2103', 'SaldoFinal': Decimal('100')}
                    for fecha in kwargs['fechas']]
    resultado = ResumenSpreadTasaService(VerificarFechas()).consultar(date(2026, 1, 31))
    assert resultado.dias_con_datos == 2


def test_saldo_ausente_y_denominador_cero():
    class Ceros(Repo):
        def get_saldos_contables_con_neteo(self, **kwargs):
            return []
        def get_saldos_contables_fechas_con_neteo(self, **kwargs):
            return [{'Fecha': datetime(2026, 2, 2), 'CodigoCuenta': '2103', 'SaldoFinal': 0}]
    i = ResumenSpreadTasaService(Ceros()).consultar(date(2026, 2, 2)).indicadores
    assert i.spread_tasa is None and i.costo_promedio_fondeo is None
    assert i.inmobiliario_por_vencer is None


@pytest.mark.parametrize('codigo', ['1404', '2103'])
def test_spread_es_nulo_si_falta_un_denominador(codigo):
    class UnSoloPromedio(Repo):
        def get_saldos_contables_fechas_con_neteo(self, **kwargs):
            return [{'Fecha': datetime(2026, 2, 2), 'CodigoCuenta': codigo, 'SaldoFinal': Decimal('100')}]
    indicadores = ResumenSpreadTasaService(UnSoloPromedio()).consultar(date(2026, 2, 2)).indicadores
    assert indicadores.spread_tasa is None


def test_sin_fecha_corte_devuelve_404():
    class SinCorte(Repo):
        def get_saldos_contables_fechas_con_neteo(self, **kwargs):
            return [{'Fecha': datetime(2026, 1, 1), 'CodigoCuenta': '14', 'SaldoFinal': 10}]
    with pytest.raises(HTTPException) as exc:
        ResumenSpreadTasaService(SinCorte()).consultar(date(2026, 2, 2))
    assert exc.value.status_code == 404


def test_endpoint_autenticacion_y_respuesta_numerica():
    app = FastAPI()
    app.include_router(router, prefix='/analytic')
    app.dependency_overrides[get_resumen_spread_tasa_service] = lambda: ResumenSpreadTasaService(Repo())
    client = TestClient(app)
    url = '/analytic/spread-tasa/resumen-spread-tasa'
    assert client.post(url, json={'fecha_corte': '2026-02-02'}).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json={'fecha_corte': '2026-02-02'})
    assert response.status_code == 200
    assert isinstance(response.json()['indicadores']['spread_tasa'], float)
    assert 'costo_provisiones' not in response.json()['indicadores']
    assert 'costo_operacional' not in response.json()['indicadores']
    assert 'costo_total' not in response.json()['indicadores']
    assert response.json()['id_agencia'] == 0
    assert response.json()['id_agencia_contable'] == 1
    assert client.post(url, json={'fecha_corte': 'no-fecha'}).status_code == 422
    assert client.post(url, json={'fecha_corte': '2026-02-02', 'id_agencia': -1}).status_code == 422


def test_endpoint_filtra_saldos_y_promedios_por_agencia():
    app = FastAPI()
    app.include_router(router, prefix='/analytic')
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    app.dependency_overrides[get_resumen_spread_tasa_service] = lambda: ResumenSpreadTasaService(Repo(2))
    response = TestClient(app).post('/analytic/spread-tasa/resumen-spread-tasa', json={
        'fecha_corte': '2026-02-02', 'id_agencia': 2,
    })
    assert response.status_code == 200
    assert response.json()['id_agencia'] == 2
    assert response.json()['id_agencia_contable'] == 2


def test_spread_por_agencias_una_consulta_y_mismos_calculos():
    base = Repo()
    class Batch:
        llamadas = 0
        def obtener_saldos(self, *, fechas, ids_agencia, codigos_cuenta):
            self.llamadas += 1
            assert ids_agencia == [2, 3]
            assert fechas == [datetime(2025, 12, 31), datetime(2026, 1, 31), datetime(2026, 2, 2)]
            assert '41' in codigos_cuenta and '1401' in codigos_cuenta
            filas = base.get_saldos_contables_fechas_con_neteo(
                id_agencia=1, preservar_decimal=True, fechas=fechas,
                codigos_cuenta=CUENTAS_PROMEDIO)
            corte = base.get_saldos_contables_con_neteo(
                id_agencia=1, preservar_decimal=True, codigos_cuenta=['41'])
            return ([{'IdAgencia': 2, **fila} for fila in filas]
                    + [{'IdAgencia': 2, 'Fecha': fechas[-1], **fila} for fila in corte])
    batch = Batch()
    service = ResumenSpreadTasaService(base, batch)
    individual = service.consultar(date(2026, 2, 2)).indicadores
    tabla = service.consultar_agencias(date(2026, 2, 2), [2, 3, 2])
    assert batch.llamadas == 1
    assert [fila.id_agencia for fila in tabla.agencias] == [2, 3]
    assert tabla.agencias[0].spread_tasa == pytest.approx(individual.spread_tasa)
    assert tabla.agencias[0].costo_promedio_fondeo == pytest.approx(individual.costo_promedio_fondeo)
    assert tabla.agencias[0].rendimiento_cartera_por_vencer == pytest.approx(individual.rendimiento_cartera_por_vencer)
    assert tabla.agencias[1].spread_tasa is None


def test_endpoint_spread_por_agencia_requiere_autenticacion_y_valida_ids():
    class Batch:
        def obtener_saldos(self, **kwargs):
            return []
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_resumen_spread_tasa_service] = lambda: ResumenSpreadTasaService(Repo(), Batch())
    client = TestClient(app)
    url = '/spread-tasa/spread-por-agencia'
    body = {'fecha_corte': '2026-02-02', 'ids_agencia': [2, 3]}
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json=body)
    assert response.status_code == 200
    assert [fila['id_agencia'] for fila in response.json()['agencias']] == [2, 3]
    assert response.json()['agencias'][0]['spread_tasa'] is None
    assert client.post(url, json={**body, 'ids_agencia': [0]}).status_code == 422
    assert client.post(url, json={**body, 'ids_agencia': []}).status_code == 422
