from datetime import date, datetime, time
from decimal import Decimal

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.modules.analytic.spread_tasa.historico_rendimientos.dependencies import get_historico_rendimientos_service
from app.modules.analytic.spread_tasa.historico_rendimientos.router import router
from app.modules.analytic.spread_tasa.historico_rendimientos.schemas import HistoricoRendimientosInput
from app.modules.analytic.spread_tasa.historico_rendimientos.service import HistoricoRendimientosService
from app.modules.analytic.spread_tasa.resumen_spread_tasa.service import ResumenSpreadTasaService
from app.modules.auth.dependencies import get_current_auth_context


class Repo:
    def __init__(self):
        self.llamadas = []
    def obtener_saldos(self, **kwargs):
        self.llamadas.append(kwargs)
        return [{'IdAgencia': agencia, 'Fecha': fecha, 'CodigoCuenta': cuenta,
                 'SaldoFinal': Decimal({'510420': '30', '510410': '10', '510415': '5'}.get(cuenta, '100'))}
                for agencia in kwargs['ids_agencia'] if agencia != 3
                for fecha in kwargs['fechas'] for cuenta in kwargs['codigos_cuenta']]


@pytest.fixture(autouse=True)
def hoy(monkeypatch):
    monkeypatch.setattr('app.modules.analytic.spread_tasa.historico_rendimientos.service.fecha_actual_ecuador', lambda: date(2026, 11, 16))


def test_cierres_mes_actual_agencias_y_formulas_reutilizadas():
    repo = Repo()
    service = HistoricoRendimientosService(repo)
    resultado = service.consultar(HistoricoRendimientosInput(periodo_desde='2026-10', periodo_hasta='2026-11', ids_agencia=[0, 2, 3]))
    assert len(repo.llamadas) == 1
    assert [c.fecha_corte for c in resultado.cortes] == [date(2026, 10, 31), date(2026, 11, 16)]
    assert [c.parcial for c in resultado.cortes] == [False, True]
    assert repo.llamadas[0]['fechas'][0] == datetime(2025, 12, 31)
    assert repo.llamadas[0]['ids_agencia'] == [1, 2, 3]
    assert len(resultado.datos) == 24
    micro = next(d for d in resultado.datos if d.producto == 'microcredito' and d.id_agencia == 2 and d.periodo == '2026-11')
    assert micro.intereses == 30
    assert micro.saldo_promedio == 300
    assert micro.rendimiento == pytest.approx(30 / 300 * 12 / 11)
    assert micro.cierres_con_datos == 12
    assert all(d.rendimiento is None for d in resultado.datos if d.id_agencia == 3)
    # El mismo corte debe producir los mismos cuatro rendimientos que el resumen.
    class Individual:
        def get_saldos_contables_con_neteo(self, **kwargs):
            return repo.obtener_saldos(fechas=[kwargs['fecha']], ids_agencia=[kwargs['id_agencia']], codigos_cuenta=kwargs['codigos_cuenta'])
        def get_saldos_contables_fechas_con_neteo(self, **kwargs):
            return repo.obtener_saldos(fechas=kwargs['fechas'], ids_agencia=[kwargs['id_agencia']], codigos_cuenta=kwargs['codigos_cuenta'])
    resumen = ResumenSpreadTasaService(Individual()).consultar(date(2026, 11, 16), 2).indicadores
    campos = {'microcredito': 'rendimiento_microcredito_por_vencer', 'consumo': 'rendimiento_credito_consumo_por_vencer', 'inmobiliario': 'inmobiliario_por_vencer', 'cartera': 'rendimiento_cartera_por_vencer'}
    for dato in resultado.datos:
        if dato.periodo == '2026-11' and dato.id_agencia == 2:
            assert dato.rendimiento == pytest.approx(getattr(resumen, campos[dato.producto]))


def test_cambio_de_anio_reinicia_base_de_promedios():
    repo = Repo()
    resultado = HistoricoRendimientosService(repo).consultar(HistoricoRendimientosInput(periodo_desde='2025-12', periodo_hasta='2026-01'))
    assert resultado.datos[0].fecha_promedio_desde == date(2024, 12, 31)
    assert resultado.datos[0].cierres_con_datos == 13
    assert resultado.datos[4].fecha_promedio_desde == date(2025, 12, 31)
    assert resultado.datos[4].cierres_con_datos == 2


@pytest.mark.parametrize('desde,hasta', [('2026-11', '2026-10'), ('2026-11', '2026-12'), ('2020-01', '2026-01')])
def test_rechaza_rangos_invalidos_antes_de_consultar(desde, hasta):
    repo = Repo()
    with pytest.raises(HTTPException):
        HistoricoRendimientosService(repo).consultar(HistoricoRendimientosInput(periodo_desde=desde, periodo_hasta=hasta))
    assert not repo.llamadas


def test_endpoint_autenticacion_y_contrato():
    app = FastAPI(); app.include_router(router)
    app.dependency_overrides[get_historico_rendimientos_service] = lambda: HistoricoRendimientosService(Repo())
    client = TestClient(app); url = '/spread-tasa/historico-rendimientos'
    body = {'periodo_desde': '2026-10', 'periodo_hasta': '2026-11', 'ids_agencia': [0, 2]}
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    respuesta = client.post(url, json=body)
    assert respuesta.status_code == 200
    assert isinstance(respuesta.json()['datos'][0]['rendimiento'], float)
    assert client.post(url, json={**body, 'periodo_desde': '2026-13'}).status_code == 422
    assert client.post(url, json={**body, 'ids_agencia': []}).status_code == 422
