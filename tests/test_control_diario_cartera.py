from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.cartera_de_credito.control_diario_cartera.dependencies import get_control_diario_cartera_service
from app.modules.negocios.cartera_de_credito.control_diario_cartera.domain import CorteAsesor, CortesControlCartera
from app.modules.negocios.cartera_de_credito.control_diario_cartera.repositories.mongo_control_diario_cartera_repository import (
    MongoControlDiarioCarteraRepository, _fecha_actual,
)
from app.modules.negocios.cartera_de_credito.control_diario_cartera.router import router
from app.modules.negocios.cartera_de_credito.control_diario_cartera.schemas import ControlDiarioCarteraRequest
from app.modules.negocios.cartera_de_credito.control_diario_cartera.service import ControlDiarioCarteraService


class FakeRepository:
    def __init__(self, filas=(), fechas=()):
        self.cortes = CortesControlCartera(set(fechas) | {fila.fecha for fila in filas}, list(filas))
        self.calls = []

    def obtener_cortes(self, **kwargs):
        self.calls.append(kwargs)
        return self.cortes


def corte(fecha, saldo, *, asesor='A1', agencia='MATRIZ', cargo='ASESOR', provision='10', improductiva='20'):
    return CorteAsesor(date.fromisoformat(fecha), asesor, asesor, cargo, agencia,
                       Decimal(saldo), Decimal(improductiva), Decimal(provision))


def consultar(repository, mes='2026-10', limite=date(2026, 10, 15), **kwargs):
    return ControlDiarioCarteraService(repository).obtener(
        ControlDiarioCarteraRequest(mes=mes, **kwargs), fecha_limite=limite,
    )


def test_calcula_deltas_con_dia_anterior_y_cierre_previo_sin_redondeo_binario():
    repo = FakeRepository([
        corte('2026-09-30', '100.10', provision='5', improductiva='10'),
        corte('2026-10-01', '120.20', provision='7', improductiva='8'),
        corte('2026-10-02', '110.30', provision='6', improductiva='15'),
    ])
    respuesta = consultar(repo)
    assert len(respuesta.dias) == 31
    assert respuesta.dias[0].fecha_anterior == date(2026, 9, 30)
    assert respuesta.filas[0].variaciones[0].model_dump() == {
        'saldo_capital': 20.1, 'cartera_improductiva': -2, 'provisiones': 2,
    }
    assert respuesta.filas[0].variaciones[1].saldo_capital == -9.9
    assert repo.calls == [dict(desde=date(2026, 9, 30), hasta=date(2026, 10, 15), agencia=None, filtrar_diferidos=None)]


def test_no_compara_con_ultimo_corte_disponible_si_falta_dia_intermedio():
    respuesta = consultar(FakeRepository([
        corte('2026-09-30', '100'), corte('2026-10-01', '120'), corte('2026-10-03', '150'),
        corte('2026-10-04', '155'),
    ]))
    valores = respuesta.filas[0].variaciones
    assert valores[1] is None
    assert valores[2] is None
    assert valores[3].saldo_capital == 5
    assert all(valor is None for valor in valores[4:])


def test_corte_existente_sin_asesor_equivale_a_cero_y_conserva_bajas_y_altas():
    respuesta = consultar(FakeRepository([
        corte('2026-09-30', '100', asesor='SALE'),
        corte('2026-10-01', '50', asesor='ENTRA'),
    ]))
    filas = {fila.codigo_asesor: fila for fila in respuesta.filas}
    assert filas['SALE'].variaciones[0].saldo_capital == -100
    assert filas['ENTRA'].variaciones[0].saldo_capital == 50


def test_mismo_asesor_en_dos_agencias_no_se_mezcla_y_cargo_es_ultimo_del_mes():
    respuesta = consultar(FakeRepository([
        corte('2026-09-30', '100', cargo='ANTERIOR'),
        corte('2026-10-01', '130', cargo='NUEVO'),
        corte('2026-09-30', '40', agencia='SUR'),
        corte('2026-10-01', '30', agencia='SUR'),
    ]))
    assert len(respuesta.filas) == 2
    assert respuesta.filas[0].cargo == 'NUEVO'
    assert [fila.variaciones[0].saldo_capital for fila in respuesta.filas] == [30, -10]


@pytest.mark.parametrize('mes,dias,desde,hasta', [
    ('2024-02', 29, date(2024, 1, 31), date(2024, 2, 29)),
    ('2025-02', 28, date(2025, 1, 31), date(2025, 2, 28)),
    ('2026-01', 31, date(2025, 12, 31), date(2026, 1, 31)),
])
def test_limites_calendario_y_consulta_unica(mes, dias, desde, hasta):
    repo = FakeRepository()
    respuesta = consultar(repo, mes, agencia=' MATRIZ ', filtrar_diferidos=False)
    assert len(respuesta.dias) == dias
    assert respuesta.filas == []
    assert repo.calls == [dict(desde=desde, hasta=hasta, agencia='MATRIZ', filtrar_diferidos=False)]


def test_mes_futuro_rechazado_antes_de_consultar_mongo():
    repo = FakeRepository()
    with pytest.raises(HTTPException) as exc:
        consultar(repo, '2026-11')
    assert exc.value.status_code == 400
    assert repo.calls == []


@pytest.mark.parametrize('mes', ['2026-13', '2026-00', '26-01', '0000-01', '9999-12'])
def test_contrato_valida_mes(mes):
    with pytest.raises(ValidationError):
        ControlDiarioCarteraRequest(mes=mes)


def test_endpoint_valida_bearer_y_usa_fecha_del_sistema():
    app = FastAPI()
    app.include_router(router, prefix='/negocios')
    repo = FakeRepository()
    app.dependency_overrides[get_control_diario_cartera_service] = lambda: ControlDiarioCarteraService(repo)
    client = TestClient(app)
    ruta = '/negocios/cartera-de-credito/control-diario-cartera/mensual'
    assert client.post(ruta, json={'mes': '2026-10'}).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: AuthContext(
        token='test', usuario=UsuarioTokenPayload(
            sub='1', usuario='TEST', id_agencia=1, fecha_sistema=date(2026, 10, 8),
        ),
    )
    response = client.post(ruta, json={'mes': '2026-10', 'agencia': 'MATRIZ', 'filtrar_diferidos': True})
    assert response.status_code == 200
    assert repo.calls[0]['hasta'] == date(2026, 10, 8)
    assert response.json()['filtrar_diferidos'] is True
    assert client.post(ruta, json={'mes': '2026-11'}).status_code == 400
    assert client.post(ruta, json={'mes': '2026-15'}).status_code == 422


class FakeCollection:
    def __init__(self, fechas=(), rows=(), ultimo=None):
        self.fechas = fechas
        self.rows = rows
        self.ultimo = ultimo
        self.calls = []

    def distinct(self, campo, filtro, **options):
        self.calls.append(('distinct', campo, filtro, options))
        return self.fechas

    def aggregate(self, pipeline, **options):
        self.calls.append(('aggregate', pipeline, options))
        return self.rows

    def find_one(self, *args, **kwargs):
        return self.ultimo


def row(fecha, saldo):
    return {'_id': {'fecha': fecha, 'codigo': 'A', 'agencia': 'MATRIZ'}, 'nombre': 'Asesor', 'cargo': 'ASESOR',
            'saldo_capital': saldo, 'cartera_improductiva': 10, 'provisiones': 5}


def test_repositorio_agrupa_mes_en_mongo_con_indice_y_completa_solo_fecha_actual():
    historico = FakeCollection(['20260930', '20261001'], [row('20261001', 100)])
    actual = FakeCollection(rows=[row('20261002', 120)], ultimo={'as_of': datetime(2026, 10, 2, 15)})
    repo = MongoControlDiarioCarteraRepository({'SituacionCrediticia': historico, 'SituacionCrediticiaActual': actual})
    cortes = repo.obtener_cortes(desde=date(2026, 9, 30), hasta=date(2026, 10, 2), agencia='MATRIZ', filtrar_diferidos=False)
    assert cortes.fechas == {date(2026, 9, 30), date(2026, 10, 1), date(2026, 10, 2)}
    assert len(cortes.asesores) == 2
    llamada = historico.calls[1]
    assert llamada[2]['hint'] == 'fecha_corte_1_estado_prestamo_1'
    assert llamada[1][0]['$match']['Agencia'] == 'MATRIZ'
    assert llamada[1][0]['$match']['fecha_corte'] == {'$gte': '20260930', '$lte': '20261002'}
    assert '$group' in llamada[1][-1]
    assert len(actual.calls) == 1


@pytest.mark.parametrize('ultimo', [datetime(2026, 10, 1, 15), datetime(2026, 11, 1, 15), None])
def test_no_duplica_actual_historico_ni_usa_corte_fuera_de_mes(ultimo):
    historico = FakeCollection(['20261001'])
    actual = FakeCollection(ultimo={'as_of': ultimo} if ultimo else None)
    repo = MongoControlDiarioCarteraRepository({'SituacionCrediticia': historico, 'SituacionCrediticiaActual': actual})
    repo.obtener_cortes(desde=date(2026, 9, 30), hasta=date(2026, 10, 31), agencia=None, filtrar_diferidos=None)
    assert actual.calls == []


def test_fecha_actual_convierte_timestamp_utc_a_fecha_local():
    assert _fecha_actual(datetime(2026, 10, 2, 2)) == date(2026, 10, 1)
    assert _fecha_actual('20261002') == date(2026, 10, 2)
    assert _fecha_actual('invalida') is None
