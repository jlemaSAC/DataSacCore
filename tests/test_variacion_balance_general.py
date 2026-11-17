from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.analytic.evolucion_cuentas.router import router
from app.modules.analytic.evolucion_cuentas.variacion_balance_general import schemas
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.dependencies import get_variacion_balance_service
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import ConsultaVariacion
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.service import VariacionBalanceService, fecha_anterior


@pytest.fixture(autouse=True)
def hoy(monkeypatch):
    monkeypatch.setattr(schemas, 'fecha_actual_ecuador', lambda: date(2026, 11, 17))


class Repo:
    def __init__(self, filas=()):
        self.filas = filas
        self.consultas = []
    def obtener_agencia(self, id_agencia):
        return {'nombre': 'CONSOLIDADO', 'id_empresa': 1} if id_agencia == 1 else None
    def obtener_saldos_fechas(self, **kwargs):
        self.consultas.append(kwargs)
        return [row for row in self.filas if row['fecha'] in kwargs['fechas']]


def fila(fecha, codigo, saldo):
    return {'fecha': date.fromisoformat(fecha), 'codigo_cuenta': codigo, 'saldo': Decimal(saldo)}


@pytest.mark.parametrize('actual,tipo,esperado', [
    ('2024-02-29', 'anual', '2023-02-28'), ('2025-03-31', 'mensual', '2025-02-28'),
    ('2024-03-31', 'mensual', '2024-02-29'), ('2026-01-15', 'mensual', '2025-12-15'),
    ('2026-01-15', 'anual', '2025-01-15'),
])
def test_fechas_equivalentes(actual, tipo, esperado):
    assert fecha_anterior(date.fromisoformat(actual), tipo).isoformat() == esperado


def test_variacion_neteo_ceros_y_faltantes():
    repo = Repo([fila('2026-03-31', '1', '100.00'), fila('2026-02-28', '1', '80.00'),
                 fila('2026-03-31', '1908', '5.00'), fila('2026-02-28', '1908', '1.00'),
                 fila('2026-03-31', '2', '0.00'), fila('2026-02-28', '2', '0.00'),
                 fila('2026-03-31', '3', '10.00')])
    consulta = ConsultaVariacion(tipo='mensual', fecha_desde='2026-03-31', fecha_hasta='2026-03-31')
    corte = VariacionBalanceService(repo).consultar(consulta).datos[0]
    assert corte.fecha_comparacion == date(2026, 2, 28)
    assert corte.activos == Decimal('16.00')
    assert corte.pasivos == Decimal('0.00')
    assert corte.patrimonio is None and corte.cuentas_sin_saldo == ['3']
    assert VariacionBalanceService(repo).consultar(consulta.model_copy(update={'neteo': 0})).datos[0].activos == Decimal('20.00')


def test_rango_y_lotes_sql():
    repo = Repo()
    consulta = ConsultaVariacion(tipo='anual', fecha_desde='2022-11-18', fecha_hasta='2026-11-17')
    respuesta = VariacionBalanceService(repo).consultar(consulta)
    assert len(respuesta.datos) == 1461
    assert len(repo.consultas) > 1 and all(len(c['fechas']) <= 500 for c in repo.consultas)
    with pytest.raises(ValidationError):
        ConsultaVariacion(tipo='anual', fecha_desde='2022-11-17', fecha_hasta='2026-11-17')
    ConsultaVariacion(tipo='mensual', fecha_desde='2025-11-18', fecha_hasta='2026-11-17')
    with pytest.raises(ValidationError):
        ConsultaVariacion(tipo='mensual', fecha_desde='2025-11-17', fecha_hasta='2026-11-17')


def test_endpoint_bearer_y_respuesta():
    app = FastAPI()
    app.include_router(router, prefix='/analytic')
    app.dependency_overrides[get_variacion_balance_service] = lambda: VariacionBalanceService(Repo())
    client = TestClient(app)
    url = '/analytic/evolucion-de-cuentas/variacion-balance-general'
    body = {'tipo': 'mensual', 'fecha_desde': '2026-03-31', 'fecha_hasta': '2026-03-31'}
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    respuesta = client.post(url, json=body)
    assert respuesta.status_code == 200
    assert respuesta.json()['datos'][0]['fecha_comparacion'] == '2026-02-28'
    assert respuesta.json()['datos'][0]['activos'] is None
    assert client.post(url, json={**body, 'id_agencia': 999}).status_code == 404


def test_un_dia_por_mes_respeta_rango_y_ajusta_febrero():
    repo = Repo()
    consulta = ConsultaVariacion(tipo='anual', fecha_desde='2024-01-20', fecha_hasta='2024-04-15', dia_mes=31)
    datos = VariacionBalanceService(repo).consultar(consulta).datos
    assert [(c.fecha.isoformat(), c.fecha_comparacion.isoformat()) for c in datos] == [
        ('2024-01-31', '2023-01-31'), ('2024-02-29', '2023-02-28'), ('2024-03-31', '2023-03-31')]
    assert len(repo.consultas) == 1
    assert len(repo.consultas[0]['fechas']) == 6
    vacio = ConsultaVariacion(tipo='anual', fecha_desde='2024-04-01', fecha_hasta='2024-04-10', dia_mes=15)
    assert VariacionBalanceService(repo).consultar(vacio).datos == []


@pytest.mark.parametrize('cambios', [{'dia_mes': 0}, {'dia_mes': 32}, {'dia_mes': 15, 'tipo': 'mensual'}])
def test_dia_mes_invalido(cambios):
    with pytest.raises(ValidationError):
        ConsultaVariacion(**{'tipo': 'anual', 'fecha_desde': '2024-01-01', 'fecha_hasta': '2024-04-30', **cambios})


@pytest.mark.parametrize('tipo,esperado', [
    ('mensual_cortes', [('2024-01-31', '2023-12-31'), ('2024-02-29', '2024-01-31'), ('2024-03-31', '2024-02-29')]),
    ('anual_meses', [('2024-01-31', '2023-01-31'), ('2024-02-29', '2023-02-28'), ('2024-03-31', '2023-03-31')]),
])
def test_cortes_usan_dia_de_referencia_en_ambos_periodos(tipo, esperado):
    consulta = ConsultaVariacion(tipo=tipo, fecha_desde='2024-01-01', fecha_hasta='2024-03-31')
    datos = VariacionBalanceService(Repo()).consultar(consulta).datos
    assert [(c.fecha.isoformat(), c.fecha_comparacion.isoformat()) for c in datos] == esperado


def test_anual_diaria_compara_cada_dia_con_ano_anterior():
    consulta = ConsultaVariacion(tipo='anual', fecha_desde='2024-02-28', fecha_hasta='2024-03-01')
    datos = VariacionBalanceService(Repo()).consultar(consulta).datos
    assert [(c.fecha.isoformat(), c.fecha_comparacion.isoformat()) for c in datos] == [
        ('2024-02-28', '2023-02-28'), ('2024-02-29', '2023-02-28'), ('2024-03-01', '2023-03-01')]


def test_mensual_diaria_compara_cada_dia_y_ajusta_el_mes_anterior():
    consulta = ConsultaVariacion(tipo='mensual', fecha_desde='2024-03-29', fecha_hasta='2024-04-01')
    datos = VariacionBalanceService(Repo()).consultar(consulta).datos
    assert [(c.fecha.isoformat(), c.fecha_comparacion.isoformat()) for c in datos] == [
        ('2024-03-29', '2024-02-29'), ('2024-03-30', '2024-02-29'),
        ('2024-03-31', '2024-02-29'), ('2024-04-01', '2024-03-01')]
