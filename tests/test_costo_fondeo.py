from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.modules.analytic.spread_tasa.calculos import TIPOS_COSTO
from app.modules.analytic.spread_tasa.constants import FUENTES_FONDEO
from app.modules.analytic.spread_tasa.costo_de_fondeo.dependencies import get_costo_fondeo_service
from app.modules.analytic.spread_tasa.costo_de_fondeo.router import router
from app.modules.analytic.spread_tasa.costo_de_fondeo.schemas import CostoFondeoInput
from app.modules.analytic.spread_tasa.costo_de_fondeo.service import CostoFondeoService
from app.modules.analytic.spread_tasa.resumen_spread_tasa.service import ResumenSpreadTasaService
from app.modules.auth.dependencies import get_current_auth_context


class Repo:
    def __init__(self):
        self.llamadas = []

    def obtener_saldos(self, **kwargs):
        self.llamadas.append(kwargs)
        filas = []
        for agencia in kwargs['ids_agencia']:
            if agencia == 3:  # Agencia sin datos.
                continue
            for fecha in kwargs['fechas']:
                for cuenta in kwargs['codigos_cuenta']:
                    if cuenta in ('410130', '410115', '4103', '41'):
                        saldo = {'410130': '10.125', '410115': '4', '4103': '3', '41': '24.5'}[cuenta]
                    else:
                        # Saldo distinto en diciembre, para verificar la base del promedio.
                        saldo = '200' if fecha.month == 12 else '100'
                    filas.append({'IdAgencia': agencia, 'Fecha': fecha,
                                  'CodigoCuenta': cuenta, 'SaldoFinal': Decimal(saldo)})
        return filas


@pytest.fixture(autouse=True)
def hoy(monkeypatch):
    monkeypatch.setattr(
        'app.modules.analytic.spread_tasa.costo_de_fondeo.service.fecha_actual_ecuador',
        lambda: date(2026, 11, 16),
    )


def test_costos_en_una_consulta_y_coinciden_con_resumen():
    repo = Repo()
    resultado = CostoFondeoService(repo).consultar(CostoFondeoInput(
        periodo_desde='2026-10', periodo_hasta='2026-11', ids_agencia=[0, 1, 2, 3, 2],
    ))
    assert len(repo.llamadas) == 1
    llamada = repo.llamadas[0]
    assert llamada['ids_agencia'] == [1, 2, 3]
    assert llamada['fechas'][0] == datetime(2025, 12, 31)
    assert all(f.day == 31 or f == datetime(2026, 11, 16) or f.month in (2, 4, 6, 9)
               for f in llamada['fechas'])
    assert '41' in llamada['codigos_cuenta'] and '4101' not in llamada['codigos_cuenta']
    assert set(FUENTES_FONDEO) <= set(llamada['codigos_cuenta'])
    assert [c.fecha_corte for c in resultado.cortes] == [date(2026, 10, 31), date(2026, 11, 16)]
    assert [c.parcial for c in resultado.cortes] == [False, True]
    assert len(resultado.datos) == 24
    assert all(d.costo is None for d in resultado.datos if d.id_agencia == 3)
    plazo = next(d for d in resultado.datos if d.id_agencia == 2 and d.periodo == '2026-11'
                 and d.tipo_costo == 'ahorro_plazo')
    promedio = (200 + 11 * 100) / 12
    assert plazo.intereses == 10.125
    assert plazo.saldo_promedio == pytest.approx(promedio)
    assert plazo.costo == pytest.approx(10.125 / promedio * 12 / 11)
    assert plazo.cierres_con_datos == 12
    fondeo = next(d for d in resultado.datos if d.id_agencia == 2 and d.periodo == '2026-11'
                  and d.tipo_costo == 'promedio_fondeo')
    assert fondeo.saldo_promedio == pytest.approx(promedio * len(FUENTES_FONDEO))
    assert fondeo.costo == pytest.approx(24.5 / (promedio * len(FUENTES_FONDEO)) * 12 / 11)

    class Individual:
        def get_saldos_contables_con_neteo(self, **kw):
            return repo.obtener_saldos(fechas=[kw['fecha']], ids_agencia=[kw['id_agencia']], codigos_cuenta=kw['codigos_cuenta'])

        def get_saldos_contables_fechas_con_neteo(self, **kw):
            return repo.obtener_saldos(fechas=kw['fechas'], ids_agencia=[kw['id_agencia']], codigos_cuenta=kw['codigos_cuenta'])

    resumen = ResumenSpreadTasaService(Individual()).consultar(date(2026, 11, 16), 2).indicadores
    for dato in resultado.datos:
        if dato.id_agencia == 2 and dato.periodo == '2026-11':
            assert dato.costo == pytest.approx(getattr(resumen, 'costo_' + dato.tipo_costo))


def test_cambio_anio_y_solo_cierres():
    repo = Repo()
    resultado = CostoFondeoService(repo).consultar(CostoFondeoInput(
        periodo_desde='2025-12', periodo_hasta='2026-01',
    ))
    assert resultado.datos[0].fecha_promedio_desde == date(2024, 12, 31)
    assert resultado.datos[0].cierres_con_datos == 13
    assert resultado.datos[4].fecha_promedio_desde == date(2025, 12, 31)
    assert resultado.datos[4].cierres_con_datos == 2
    assert datetime(2026, 1, 30) not in repo.llamadas[0]['fechas']


def test_denominadores_cero_y_corte_sin_datos():
    class Ceros:
        def obtener_saldos(self, **kwargs):
            return [{'IdAgencia': 1, 'Fecha': fecha, 'CodigoCuenta': '2103', 'SaldoFinal': Decimal(0)}
                    for fecha in kwargs['fechas'] if fecha < datetime(2026, 11, 1)]

    resultado = CostoFondeoService(Ceros()).consultar(CostoFondeoInput(
        periodo_desde='2026-10', periodo_hasta='2026-11',
    ))
    assert all(d.costo is None for d in resultado.datos)
    assert resultado.datos[0].intereses == 0
    assert resultado.datos[4].intereses is None


@pytest.mark.parametrize('desde,hasta', [
    ('2026-11', '2026-10'), ('2026-11', '2026-12'), ('2020-01', '2026-01'),
])
def test_rechaza_rango_invalido_sin_consultar(desde, hasta):
    repo = Repo()
    with pytest.raises(HTTPException):
        CostoFondeoService(repo).consultar(CostoFondeoInput(periodo_desde=desde, periodo_hasta=hasta))
    assert not repo.llamadas


def test_endpoint_bearer_y_contrato_numerico():
    app = FastAPI()
    app.include_router(router, prefix='/analytic')
    app.dependency_overrides[get_costo_fondeo_service] = lambda: CostoFondeoService(Repo())
    client = TestClient(app)
    url = '/analytic/spread-tasa/costo-de-fondeo'
    body = {'periodo_desde': '2026-10', 'periodo_hasta': '2026-11', 'ids_agencia': [0, 2]}
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json=body)
    assert response.status_code == 200
    assert isinstance(response.json()['datos'][0]['costo'], float)
    assert set(d['tipo_costo'] for d in response.json()['datos']) == set(TIPOS_COSTO)
    for extra in ({'periodo_desde': '2026-13'}, {'ids_agencia': []}, {'ids_agencia': [-1]}):
        assert client.post(url, json={**body, **extra}).status_code == 422
