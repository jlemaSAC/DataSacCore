from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.analytic.analisis_contable.router import router
from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.dependencies import get_comparativa_cuentas_service
from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.schemas import ConsultaComparativaCuentas
from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.service import ComparativaCuentasService


class Repositorio:
    def __init__(self, filas=()):
        self.filas = list(filas)
        self.consultas = []

    def obtener_agencia(self, id_agencia):
        return dict(nombre="CONSOLIDADO" if id_agencia == 1 else "MATRIZ", id_empresa=1) if id_agencia in (1, 2) else None

    def obtener_cuentas(self, empresa):
        return [
            dict(codigo_cuenta=codigo, nombre_cuenta=codigo, codigo_padre=padre,
                 activa=activa, es_movimiento=movimiento)
            for codigo, padre, activa, movimiento in [
                ("1", None, True, False), ("14", "1", True, False),
                ("1401", "14", True, True), ("140105", "1401", False, True),
                ("1908", "1", True, True),
                ("2", None, True, False),
            ]
        ]

    def obtener_saldos(self, **kwargs):
        self.consultas.append(kwargs)
        return self.filas


def fila(fecha, codigo, saldo):
    return dict(fecha=date.fromisoformat(fecha), codigo_cuenta=codigo, saldo=Decimal(saldo))


@pytest.mark.parametrize("inicio,corte,esperadas", [
    ("2026-05", "2026-10-15", [f"2026-{mes:02}-15" for mes in range(5, 11)]),
    ("2026-01", "2026-03-31", ["2026-01-31", "2026-02-28", "2026-03-31"]),
    ("2024-01", "2024-03-31", ["2024-01-31", "2024-02-29", "2024-03-31"]),
    ("2025-11", "2026-02-28", ["2025-11-28", "2025-12-28", "2026-01-28", "2026-02-28"]),
    ("2026-10", "2026-10-15", ["2026-10-15"]),
    ("2024-11", "2026-10-15", [f"{year}-{month:02}-15" for year, month in [(2024, 11), (2024, 12)] + [(2025, m) for m in range(1, 13)] + [(2026, m) for m in range(1, 11)]]),
])
def test_calendario_anclado_al_dia_final_y_una_consulta_de_saldos(inicio, corte, esperadas):
    repo = Repositorio()
    respuesta = ComparativaCuentasService(repo).consultar(ConsultaComparativaCuentas(mes_inicio=inicio, fecha_corte=corte))
    assert [p.fecha.isoformat() for p in respuesta.periodos] == esperadas
    assert [p.fecha_ajustada for p in respuesta.periodos] == [int(f[-2:]) != int(corte[-2:]) for f in esperadas]
    assert len(repo.consultas) == 1
    assert repo.consultas[0] == dict(fechas=[date.fromisoformat(f) for f in esperadas], id_agencia=1, id_empresa=1)
    assert all(p.cuentas_con_datos == 0 for p in respuesta.periodos)
    assert respuesta.total_cuentas == 5


def test_variaciones_decimales_ceros_ausencias_solo_activas_y_jerarquia():
    repo = Repositorio([
        fila("2026-01-15", "14", "100.01"), fila("2026-02-15", "14", "0.00"), fila("2026-03-15", "14", "-20.02"),
        fila("2026-01-15", "1401", "1.00"), fila("2026-03-15", "1401", "2.00"),
        fila("2026-01-15", "140105", "10.00"), fila("2026-03-15", "140105", "0.00"),
    ])
    respuesta = ComparativaCuentasService(repo).consultar(ConsultaComparativaCuentas(mes_inicio="2026-01", fecha_corte="2026-03-15", neteo=0, id_agencia=2))
    cuentas = {c.codigo_cuenta: c for c in respuesta.cuentas}
    assert [v.variacion_absoluta for v in cuentas["14"].valores] == [None, Decimal("-100.01"), Decimal("-20.02")]
    assert cuentas["14"].valores[1].saldo == Decimal("0.00")
    assert all(c.activa for c in respuesta.cuentas)
    assert "140105" not in cuentas
    assert respuesta.total_cuentas == 5
    assert cuentas["1401"].nivel == 3
    assert [v.saldo for v in cuentas["1401"].valores] == [Decimal("1.00"), None, Decimal("2.00")]
    assert all(v.variacion_absoluta is None for v in cuentas["1401"].valores)
    assert all(v.saldo is None for v in cuentas["2"].valores)
    assert [p.cuentas_con_datos for p in respuesta.periodos] == [2, 1, 2]
    assert repo.consultas[0]["id_agencia"] == 2


def test_ajuste_inactivo_interviene_en_neteo_pero_no_se_muestra():
    class Repo(Repositorio):
        def obtener_cuentas(self, empresa):
            return [{**c, "activa": False} if c["codigo_cuenta"] == "1908" else c
                    for c in super().obtener_cuentas(empresa)]

    respuesta = ComparativaCuentasService(Repo([
        fila("2026-10-15", "1", "100.01"), fila("2026-10-15", "1908", "20.00"),
    ])).consultar(ConsultaComparativaCuentas(mes_inicio="2026-10", fecha_corte="2026-10-15"))
    cuentas = {c.codigo_cuenta: c for c in respuesta.cuentas}
    assert "1908" not in cuentas
    assert cuentas["1"].valores[0].saldo == Decimal("80.01")
    assert respuesta.periodos[0].cuentas_con_datos == 1


@pytest.mark.parametrize("neteo,esperados,variacion", [
    (1, ["0.00", "15.05"], "15.05"), (0, ["10.01", "15.05"], "5.04"),
])
def test_neteo_por_corte_sin_mutar_la_base_y_ajuste_ausente(neteo, esperados, variacion):
    repo = Repositorio([
        fila("2026-09-15", "1", "10.01"), fila("2026-09-15", "1908", "10.01"),
        fila("2026-10-15", "1", "15.05"), fila("2026-10-15", "1908", "0.00"),
        fila("2026-10-15", "2908", "5.00"),
    ])
    respuesta = ComparativaCuentasService(repo).consultar(ConsultaComparativaCuentas(mes_inicio="2026-09", fecha_corte="2026-10-15", neteo=neteo))
    cuentas = {c.codigo_cuenta: c for c in respuesta.cuentas}
    assert [v.saldo for v in cuentas["1"].valores] == list(map(Decimal, esperados))
    assert cuentas["1"].valores[-1].variacion_absoluta == Decimal(variacion)
    assert all(v.saldo is None for v in cuentas["2"].valores)  # El ajuste no inventa una cuenta base.
    assert repo.filas[0]["saldo"] == Decimal("10.01")


@pytest.mark.parametrize("inicio,corte", [
    ("2026-11", "2026-10-15"), ("2024-10", "2026-10-15"),
    ("2026-13", "2026-10-15"), ("0000-01", "2026-10-15"), ("2026-5", "2026-10-15"),
])
def test_validacion_intervalo(inicio, corte):
    with pytest.raises(ValidationError):
        ConsultaComparativaCuentas(mes_inicio=inicio, fecha_corte=corte)


def test_endpoint_bearer_contrato_precision_y_errores():
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    repo = Repositorio([fila("2026-09-15", "14", "9999999999999999.98"), fila("2026-10-15", "14", "9999999999999999.99")])
    app.dependency_overrides[get_comparativa_cuentas_service] = lambda: ComparativaCuentasService(repo)
    client = TestClient(app)
    url = "/analytic/analisis-contable/comparativa-cuentas-contables"
    body = dict(mes_inicio="2026-09", fecha_corte="2026-10-15")
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json=body)
    assert response.status_code == 200
    datos = response.json()
    assert datos["cuentas"][1]["valores"][-1] == dict(periodo="2026-10", saldo="9999999999999999.99", variacion_absoluta="0.01")
    assert datos["periodos"][0]["fecha"] == "2026-09-15"
    assert datos["id_agencia_contable"] == 1
    assert client.post(url, json={**body, "id_agencia": 999}).status_code == 404
    for cambio in [dict(neteo=2), dict(id_agencia=-1), dict(mes_inicio="2026-11"), dict(fecha_corte="2026-02-30")]:
        assert client.post(url, json={**body, **cambio}).status_code == 422


def test_comparativa_anual_bisiesto_variaciones_y_ausencias():
    repo = Repositorio([
        fila('2020-02-29', '14', '100.00'), fila('2021-02-28', '14', '150.00'),
        fila('2023-02-28', '14', '200.00'), fila('2024-02-29', '14', '210.00'),
    ])
    consulta = ConsultaComparativaCuentas(periodicidad='anual', anio_inicio=2020, fecha_corte='2024-02-29', neteo=0)
    respuesta = ComparativaCuentasService(repo).consultar(consulta)
    assert [p.fecha.isoformat() for p in respuesta.periodos] == [
        '2020-02-29', '2021-02-28', '2022-02-28', '2023-02-28', '2024-02-29']
    assert [p.fecha_ajustada for p in respuesta.periodos] == [False, True, True, True, False]
    valores = next(c.valores for c in respuesta.cuentas if c.codigo_cuenta == '14')
    assert [v.variacion_absoluta for v in valores] == [None, Decimal('50.00'), None, None, Decimal('10.00')]
    assert len(repo.consultas) == 1


def test_endpoint_anual_validacion_y_autenticacion():
    app = FastAPI()
    app.include_router(router, prefix='/analytic')
    app.dependency_overrides[get_comparativa_cuentas_service] = lambda: ComparativaCuentasService(Repositorio())
    client = TestClient(app)
    url = '/analytic/analisis-contable/comparativa-cuentas-contables'
    body = dict(periodicidad='anual', anio_inicio=2024, fecha_corte='2024-02-29')
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json=body)
    assert response.status_code == 200
    assert [p['fecha'] for p in response.json()['periodos']] == ['2024-02-29']
    for cambio in [dict(anio_inicio=2025), dict(anio_inicio=0), dict(anio_inicio=None), dict(mes_inicio='2024-02')]:
        assert client.post(url, json={**body, **cambio}).status_code == 422


def test_comparativa_diaria_fechas_unicas_variacion_ausencias_y_neteo():
    repo = Repositorio([
        fila('2024-02-28', '1', '100.00'), fila('2024-02-28', '1908', '10.00'),
        fila('2024-02-29', '1', '105.00'), fila('2024-02-29', '1908', '5.00'),
        fila('2024-03-02', '1', '150.00'),
    ])
    consulta = ConsultaComparativaCuentas(periodicidad='diaria', fecha_inicio='2024-02-28', fecha_corte='2024-03-02')
    respuesta = ComparativaCuentasService(repo).consultar(consulta)
    assert [p.periodo for p in respuesta.periodos] == ['2024-02-28', '2024-02-29', '2024-03-01', '2024-03-02']
    assert not any(p.fecha_ajustada for p in respuesta.periodos)
    valores = next(c.valores for c in respuesta.cuentas if c.codigo_cuenta == '1')
    assert [v.saldo for v in valores] == [Decimal('90.00'), Decimal('100.00'), None, Decimal('150.00')]
    assert [v.variacion_absoluta for v in valores] == [None, Decimal('10.00'), None, None]
    assert [v.periodo for v in valores] == [p.periodo for p in respuesta.periodos]
    assert len(repo.consultas) == 1 and repo.consultas[0]['rango_continuo'] is True


@pytest.mark.parametrize('inicio,fin,valido', [
    ('2024-01-31', '2024-04-30', True), ('2024-01-31', '2024-05-01', False),
    ('2024-11-30', '2025-02-28', True), ('2024-11-30', '2025-03-01', False),
    ('2024-02-29', '2024-02-29', True), ('2024-02-29', '2024-02-28', False),
    ('1752-12-31', '1753-01-01', False),
])
def test_intervalo_diario_tres_meses_calendario(inicio, fin, valido):
    datos = dict(periodicidad='diaria', fecha_inicio=inicio, fecha_corte=fin)
    if valido:
        ConsultaComparativaCuentas(**datos)
    else:
        with pytest.raises(ValidationError):
            ConsultaComparativaCuentas(**datos)


def test_endpoint_diario_auth_validacion_y_fechas():
    app = FastAPI()
    app.include_router(router, prefix='/analytic')
    app.dependency_overrides[get_comparativa_cuentas_service] = lambda: ComparativaCuentasService(Repositorio())
    client = TestClient(app)
    url = '/analytic/analisis-contable/comparativa-cuentas-contables'
    body = dict(periodicidad='diaria', fecha_inicio='2024-02-28', fecha_corte='2024-03-01')
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json=body)
    assert response.status_code == 200
    assert [p['periodo'] for p in response.json()['periodos']] == ['2024-02-28', '2024-02-29', '2024-03-01']
    for cambio in [dict(fecha_inicio=None), dict(fecha_inicio='2023-01-01'), dict(mes_inicio='2024-02'), dict(anio_inicio=2020)]:
        assert client.post(url, json={**body, **cambio}).status_code == 422


def test_repositorio_diario_consulta_rango_sin_lista_de_cortes():
    from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.repositories.sql_comparativa_cuentas_repository import SqlComparativaCuentasRepository

    class Saldos:
        def obtener_saldos(self, **kwargs):
            self.kwargs = kwargs
            return []

    repo = SqlComparativaCuentasRepository(None)
    repo.saldos = Saldos()
    fechas = [date(2024, 2, 28), date(2024, 2, 29), date(2024, 3, 1)]
    repo.obtener_saldos(fechas=fechas, id_agencia=1, id_empresa=2, rango_continuo=True)
    assert repo.saldos.kwargs == dict(fecha_desde=fechas[0], fecha_hasta=fechas[-1], id_agencia=1, id_empresa=2)


class RepositorioMovimientos(Repositorio):
    def obtener_movimientos_mensuales(self, **kwargs):
        self.consultas.append(kwargs)
        return self.filas

    def obtener_saldos(self, **kwargs):
        raise AssertionError('La variación anual por meses debe consultar movimientos, no saldos.')


def test_anual_por_meses_compara_cada_mes_con_su_anio_anterior_desde_enero():
    from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.schemas import ConsultaComparativaAnualMeses

    repo = RepositorioMovimientos([
        fila('2023-01-15', '14', '100.00'), fila('2024-01-15', '14', '120.01'),
        fila('2023-02-15', '14', '-50.00'), fila('2024-02-15', '14', '0.00'),
        fila('2024-03-15', '14', '99.00'), fila('2025-01-15', '14', '140.03'),
        fila('2025-02-15', '14', '10.00'),
    ])
    respuesta = ComparativaCuentasService(repo).consultar(ConsultaComparativaAnualMeses(
        anio_inicio=2024, fecha_corte='2025-02-15', neteo=0,
    ))
    assert len(respuesta.periodos) == 14
    assert respuesta.periodos[0].fecha == date(2024, 1, 15)
    assert respuesta.periodos[-1].fecha == date(2025, 2, 15)
    assert respuesta.periodos[-1].fecha_anterior == date(2024, 2, 15)
    valores = next(c.valores for c in respuesta.cuentas if c.codigo_cuenta == '14')
    assert valores[0].saldo_anterior == Decimal('100.00')
    assert valores[0].variacion_absoluta == Decimal('20.01')
    assert valores[1].saldo == Decimal('0.00')
    assert valores[1].variacion_absoluta == Decimal('50.00')
    assert valores[2].saldo_anterior is None and valores[2].variacion_absoluta is None
    assert valores[12].saldo_anterior == Decimal('120.01')
    assert valores[12].variacion_absoluta == Decimal('20.02')
    assert valores[13].saldo_anterior == Decimal('0.00')
    assert valores[13].variacion_absoluta == Decimal('10.00')
    assert len(repo.consultas) == 1
    fechas = repo.consultas[0]['fechas']
    assert len(fechas) == 26 and len(set(fechas)) == 26
    assert repo.consultas[0]['id_agencia'] == 1
    assert respuesta.periodos[0].cuentas_con_datos == 1
    assert respuesta.periodos[0].cuentas_con_datos_anterior == 1


def test_anual_por_meses_ajusta_cada_febrero_independientemente_y_netea_ambos_anios():
    from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.schemas import ConsultaComparativaAnualMeses

    repo = RepositorioMovimientos([
        fila('2024-02-29', '1', '150.05'), fila('2024-02-29', '1908', '10.01'),
        fila('2025-02-28', '1', '200.10'), fila('2025-02-28', '1908', '20.02'),
    ])
    respuesta = ComparativaCuentasService(repo).consultar(ConsultaComparativaAnualMeses(
        anio_inicio=2025, fecha_corte='2025-03-31',
    ))
    febrero = respuesta.periodos[1]
    assert febrero.fecha == date(2025, 2, 28) and febrero.fecha_ajustada
    assert febrero.fecha_anterior == date(2024, 2, 29) and febrero.fecha_anterior_ajustada
    valor = next(c.valores for c in respuesta.cuentas if c.codigo_cuenta == '1')[1]
    assert valor.saldo == Decimal('180.08')
    assert valor.saldo_anterior == Decimal('140.04')
    assert valor.variacion_absoluta == Decimal('40.04')
    assert repo.filas[0]['saldo'] == Decimal('150.05')
    # Corte 29: febrero bisiesto conserva 29 y el año anterior se ajusta a 28.
    respuesta = ComparativaCuentasService(RepositorioMovimientos()).consultar(
        ConsultaComparativaAnualMeses(anio_inicio=2024, fecha_corte='2024-02-29'))
    assert not respuesta.periodos[1].fecha_ajustada
    assert respuesta.periodos[1].fecha_anterior == date(2023, 2, 28)
    assert respuesta.periodos[1].fecha_anterior_ajustada


def test_anual_por_meses_conserva_ausencias_y_rangos_incompletos():
    from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.schemas import ConsultaComparativaAnualMeses

    filas = [fila('2023-01-15', '1', '100.00'), fila('2024-01-15', '1', '120.00'),
             dict(fecha=date(2024, 1, 15), codigo_cuenta='1908', saldo=None),
             fila('2023-01-15', '14', '0.00')]
    respuesta = ComparativaCuentasService(RepositorioMovimientos(filas)).consultar(
        ConsultaComparativaAnualMeses(anio_inicio=2024, fecha_corte='2024-01-15'))
    cuentas = {c.codigo_cuenta: c for c in respuesta.cuentas}
    assert cuentas['1'].valores[0].saldo is None  # Ajuste con días ausentes.
    assert cuentas['1'].valores[0].saldo_anterior == Decimal('100.00')
    assert cuentas['1'].valores[0].variacion_absoluta is None
    assert cuentas['14'].valores[0].saldo is None
    assert cuentas['14'].valores[0].saldo_anterior == Decimal('0.00')
    assert respuesta.periodos[0].cuentas_con_datos == 0
    assert respuesta.periodos[0].cuentas_con_datos_anterior == 2


def test_endpoint_anual_por_meses_bearer_contrato_y_validacion():
    app = FastAPI()
    app.include_router(router, prefix='/analytic')
    repo = RepositorioMovimientos([fila('2023-01-15', '14', '10.01'), fila('2024-01-15', '14', '20.03')])
    app.dependency_overrides[get_comparativa_cuentas_service] = lambda: ComparativaCuentasService(repo)
    client = TestClient(app)
    url = '/analytic/analisis-contable/comparativa-cuentas-contables/anual-por-meses'
    body = dict(periodicidad='anual_meses', anio_inicio=2024, fecha_corte='2024-01-15')
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json=body)
    assert response.status_code == 200
    datos = response.json()
    assert datos['cuentas'][1]['valores'][0] == dict(periodo='2024-01', saldo='20.03',
                                                   saldo_anterior='10.01', variacion_absoluta='10.02')
    assert datos['periodos'][0]['fecha_anterior'] == '2023-01-15'
    assert client.post(url, json={**body, 'id_agencia': 999}).status_code == 404
    for cambio in [dict(anio_inicio=2025), dict(anio_inicio=1753), dict(anio_inicio=None),
                   dict(fecha_corte='2024-02-30'), dict(neteo=2), dict(id_agencia=-1)]:
        assert client.post(url, json={**body, **cambio}).status_code == 422
