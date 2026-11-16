from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.modules.analytic.spread_tasa.constants import CARTERA_POR_VENCER, FUENTES_FONDEO
from app.modules.analytic.spread_tasa.historico_spread_tasa.dependencies import get_historico_spread_tasa_service
from app.modules.analytic.spread_tasa.historico_spread_tasa.router import router
from app.modules.analytic.spread_tasa.historico_spread_tasa.schemas import HistoricoSpreadTasaInput
from app.modules.analytic.spread_tasa.historico_spread_tasa.service import HistoricoSpreadTasaService
from app.modules.analytic.spread_tasa.resumen_spread_tasa.service import ResumenSpreadTasaService
from app.modules.auth.dependencies import get_current_auth_context


class Repo:
    def __init__(self):
        self.llamadas = []

    def obtener_saldos(self, **kwargs):
        self.llamadas.append(kwargs)
        filas = []
        for agencia in kwargs['ids_agencia']:
            if agencia == 3:
                continue
            for fecha in kwargs['fechas']:
                for cuenta in kwargs['codigos_cuenta']:
                    if cuenta in FUENTES_FONDEO or cuenta in CARTERA_POR_VENCER:
                        saldo = Decimal('200' if fecha.month == 12 else '100')
                    else:
                        saldo = Decimal({'41': '12.5' if agencia == 1 else '100',
                                         '510420': '24.75', '510410': '10', '510415': '5'}.get(cuenta, '0'))
                    filas.append({'IdAgencia': agencia, 'Fecha': fecha,
                                  'CodigoCuenta': cuenta, 'SaldoFinal': saldo})
        return filas


@pytest.fixture(autouse=True)
def hoy(monkeypatch):
    monkeypatch.setattr(
        'app.modules.analytic.spread_tasa.historico_spread_tasa.service.fecha_actual_ecuador',
        lambda: date(2026, 11, 16),
    )


def test_una_consulta_y_tres_indicadores_coinciden_con_resumen():
    repo = Repo()
    resultado = HistoricoSpreadTasaService(repo).consultar(HistoricoSpreadTasaInput(
        periodo_desde='2026-10', periodo_hasta='2026-11', ids_agencia=[0, 1, 2, 3, 2],
    ))
    assert len(repo.llamadas) == 1
    assert repo.llamadas[0]['ids_agencia'] == [1, 2, 3]
    assert repo.llamadas[0]['fechas'] == [datetime(2025, 12, 31), *[
        datetime(2026, mes, monthrange(2026, mes)[1]) for mes in range(1, 11)
    ], datetime(2026, 11, 16)]
    assert '41' in repo.llamadas[0]['codigos_cuenta']
    assert '4101' not in repo.llamadas[0]['codigos_cuenta']
    assert [c.parcial for c in resultado.cortes] == [False, True]
    assert len(resultado.datos) == 18
    assert all(d.valor is None for d in resultado.datos if d.id_agencia == 3)

    class Individual:
        def get_saldos_contables_con_neteo(self, **kw):
            return repo.obtener_saldos(fechas=[kw['fecha']], ids_agencia=[kw['id_agencia']], codigos_cuenta=kw['codigos_cuenta'])

        def get_saldos_contables_fechas_con_neteo(self, **kw):
            return repo.obtener_saldos(fechas=kw['fechas'], ids_agencia=[kw['id_agencia']], codigos_cuenta=kw['codigos_cuenta'])

    for agencia in (0, 2):
        resumen = ResumenSpreadTasaService(Individual()).consultar(date(2026, 11, 16), agencia).indicadores
        for dato in resultado.datos:
            if dato.id_agencia == agencia and dato.periodo == '2026-11':
                assert dato.valor == pytest.approx(getattr(resumen, dato.indicador))
    spreads = [d for d in resultado.datos if d.indicador == 'spread_tasa' and d.periodo == '2026-11']
    assert spreads[0].valor > 0
    assert spreads[1].valor < 0
    for dato in spreads[:2]:
        componentes = dato.componentes
        assert dato.intereses is None and dato.saldo_promedio is None
        assert dato.valor == pytest.approx(componentes.rendimiento_cartera_por_vencer.valor - componentes.costo_promedio_fondeo.valor)
        assert dato.cierres_con_datos == 12
        promedio = (200 + 11 * 100) / 12
        assert componentes.rendimiento_cartera_por_vencer.saldo_promedio == pytest.approx(promedio * 21)
        assert componentes.costo_promedio_fondeo.saldo_promedio == pytest.approx(promedio * 19)


@pytest.mark.parametrize('cuenta', ['1401', '2103'])
def test_spread_nulo_si_un_promedio_es_cero(cuenta):
    class UnPromedio:
        def obtener_saldos(self, **kwargs):
            return [{'IdAgencia': 1, 'Fecha': fecha, 'CodigoCuenta': cuenta, 'SaldoFinal': Decimal('100')}
                    for fecha in kwargs['fechas']]

    datos = HistoricoSpreadTasaService(UnPromedio()).consultar(HistoricoSpreadTasaInput(
        periodo_desde='2026-11', periodo_hasta='2026-11',
    )).datos
    assert datos[2].valor is None
    assert datos[2].componentes is not None
    assert datos[0 if cuenta == '1401' else 1].valor is None
    assert datos[1 if cuenta == '1401' else 0].valor == 0


def test_corte_ausente_no_inventa_valores():
    class SinCorte:
        def obtener_saldos(self, **kwargs):
            return [{'IdAgencia': 1, 'Fecha': datetime(2025, 12, 31), 'CodigoCuenta': '2103', 'SaldoFinal': 100}]

    resultado = HistoricoSpreadTasaService(SinCorte()).consultar(HistoricoSpreadTasaInput(
        periodo_desde='2026-10', periodo_hasta='2026-10',
    ))
    assert all(d.valor is None and d.intereses is None for d in resultado.datos)
    assert resultado.datos[2].componentes.costo_promedio_fondeo.valor is None


def test_cambio_de_anio_reinicia_promedios():
    resultado = HistoricoSpreadTasaService(Repo()).consultar(HistoricoSpreadTasaInput(
        periodo_desde='2025-12', periodo_hasta='2026-01',
    ))
    assert resultado.datos[0].fecha_promedio_desde == date(2024, 12, 31)
    assert resultado.datos[0].cierres_con_datos == 13
    assert resultado.datos[3].fecha_promedio_desde == date(2025, 12, 31)
    assert resultado.datos[3].cierres_con_datos == 2


@pytest.mark.parametrize('desde,hasta', [
    ('2026-11', '2026-10'), ('2026-11', '2026-12'), ('2020-01', '2026-01'),
])
def test_rango_invalido_no_consulta(desde, hasta):
    repo = Repo()
    with pytest.raises(HTTPException):
        HistoricoSpreadTasaService(repo).consultar(HistoricoSpreadTasaInput(periodo_desde=desde, periodo_hasta=hasta))
    assert not repo.llamadas


def test_endpoint_autenticacion_y_contrato_numerico():
    app = FastAPI()
    app.include_router(router, prefix='/analytic')
    app.dependency_overrides[get_historico_spread_tasa_service] = lambda: HistoricoSpreadTasaService(Repo())
    client = TestClient(app)
    url = '/analytic/spread-tasa/historico-spread-de-tasa'
    body = {'periodo_desde': '2026-10', 'periodo_hasta': '2026-11', 'ids_agencia': [0, 2]}
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json=body)
    assert response.status_code == 200
    datos = response.json()['datos']
    assert {d['indicador'] for d in datos} == {'costo_promedio_fondeo', 'rendimiento_cartera_por_vencer', 'spread_tasa'}
    assert isinstance(datos[0]['valor'], float)
    assert datos[2]['componentes']['costo_promedio_fondeo']['valor'] == datos[0]['valor']
    for extra in ({'periodo_desde': '2026-13'}, {'ids_agencia': []}, {'ids_agencia': [-1]}):
        assert client.post(url, json={**body, **extra}).status_code == 422
