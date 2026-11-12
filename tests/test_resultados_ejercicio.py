from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.analytic.analisis_contable.router import router
from app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.dependencies import get_resultados_ejercicio_service
from app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.domain import FILAS
from app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.schemas import ConsultaCorteResultados, ConsultaHistoricoResultados, ConsultaHistoricoMensualResultados
from app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.service import ResultadosEjercicioService


CORTE = date(2026, 9, 30)
SALDOS_IMAGEN = {cuenta: Decimal(saldo) for cuenta, saldo in {
    "5": "25568125.49", "51": "24312804.06", "41": "16260061.75",
    "52": "274052.04", "54": "413450.40", "42": "16404.40", "53": "219885.58",
    "43": "0.00", "44": "2431464.22", "45": "6490843.12", "55": "5629.77",
    "46": "140.83", "56": "342303.64", "47": "14532.24", "48": "111783.89",
    "41019005": "6470734.04", "51909005": "6470734.04",
}.items()}


class Repositorio:
    def __init__(self, datos=None):
        self.datos = {CORTE: dict(SALDOS_IMAGEN)} if datos is None else datos
        self.consultas = []

    def obtener_agencia(self, id_agencia):
        return {"nombre": "CONSOLIDADO" if id_agencia == 1 else "MATRIZ", "id_empresa": 1} if id_agencia in (1, 2) else None

    def obtener_saldos_fechas(self, **kwargs):
        self.consultas.append(kwargs)
        return [{"fecha": fecha, "codigo_cuenta": cuenta, "saldo": saldo}
                for fecha in kwargs["fechas"] for cuenta, saldo in self.datos.get(fecha, {}).items()]


def test_corte_reproduce_las_22_filas_de_la_imagen_con_decimales_exactos():
    repo = Repositorio()
    respuesta = ResultadosEjercicioService(repo).consultar_corte(ConsultaCorteResultados(fecha_corte=CORTE))
    assert respuesta.id_agencia == 0 and respuesta.id_agencia_contable == 1
    assert respuesta.fechas == [CORTE]
    assert len(respuesta.filas) == respuesta.total_registros == 22
    assert [fila.codigo for fila in respuesta.filas] == [fila[0] for fila in FILAS]
    assert [item.saldo for item in respuesta.datos] == list(map(Decimal, [
        "19097391.45", "17842070.02", "9789327.71", "8052742.31", "274052.04", "413450.40",
        "16404.40", "219885.58", "0.00", "8943725.93", "2431464.22", "6512261.71",
        "6490843.12", "21418.59", "5629.77", "140.83", "26907.53", "342303.64",
        "14532.24", "354678.93", "111783.89", "242895.04",
    ]))
    assert sum(fila.es_resultado for fila in respuesta.filas) == 7
    assert respuesta.filas[2].signo == "-" and respuesta.filas[2].cuenta == "41"
    assert respuesta.filas[0].formula == "5 - 51909005"
    assert len(repo.consultas) == 1
    assert repo.consultas[0]["fechas"] == [CORTE]


@pytest.mark.parametrize("neteo", [0, 1])
def test_neteo_no_duplica_ajustes_ni_modifica_saldos_originales(neteo):
    repo = Repositorio()
    respuesta = ResultadosEjercicioService(repo).consultar_corte(ConsultaCorteResultados(fecha_corte=CORTE, id_agencia=2, neteo=neteo))
    assert respuesta.id_agencia_contable == repo.consultas[0]["id_agencia"] == 2
    esperado = Decimal("19097391.45") if neteo else SALDOS_IMAGEN["5"]
    assert respuesta.datos[0].saldo == esperado
    assert respuesta.datos[-1].saldo == Decimal("242895.04")
    assert repo.datos[CORTE]["5"] == SALDOS_IMAGEN["5"]
    assert ("51909005" in repo.consultas[0]["codigos_cuenta"]) == bool(neteo)


def test_diario_inclusivo_preserva_ceros_y_fechas_sin_saldos():
    repo = Repositorio()
    hasta = CORTE + timedelta(days=2)
    respuesta = ResultadosEjercicioService(repo).consultar_diario(ConsultaHistoricoResultados(fecha_desde=CORTE, fecha_hasta=hasta))
    assert respuesta.fechas == [CORTE, CORTE + timedelta(days=1), hasta]
    assert len(repo.consultas) == 1
    assert respuesta.total_registros == 66
    assert respuesta.datos[8].saldo == Decimal("0.00")
    assert all(item.saldo is None for item in respuesta.datos[22:])


def test_faltante_solo_afecta_los_subtotales_dependientes():
    saldos = dict(SALDOS_IMAGEN)
    del saldos["55"]
    repo = Repositorio({CORTE: saldos})
    respuesta = ResultadosEjercicioService(repo).consultar_corte(ConsultaCorteResultados(fecha_corte=CORTE))
    por_codigo = {item.codigo_fila: item.saldo for item in respuesta.datos}
    assert por_codigo["margen_intermediacion"] == Decimal("21418.59")
    assert por_codigo["margen_operacional"] is None
    assert por_codigo["ganancia_ejercicio"] is None
    assert por_codigo["otros_ingresos"] == Decimal("342303.64")


def test_sin_ajuste_considera_cero_y_perdida_conserva_signo():
    saldos = dict(SALDOS_IMAGEN)
    del saldos["51909005"]
    del saldos["41019005"]
    saldos["48"] = Decimal("500000.00")
    respuesta = ResultadosEjercicioService(Repositorio({CORTE: saldos})).consultar_corte(ConsultaCorteResultados(fecha_corte=CORTE))
    assert respuesta.datos[0].saldo == SALDOS_IMAGEN["5"]
    assert respuesta.datos[-1].saldo == Decimal("-145321.07")


def test_mensual_cierres_hoy_mes_actual_y_exclusion_de_futuros(monkeypatch):
    monkeypatch.setattr('app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.service.fecha_actual_ecuador', lambda: date(2026, 11, 11))
    repo = Repositorio()
    respuesta = ResultadosEjercicioService(repo).consultar_mensual(ConsultaHistoricoResultados(fecha_desde="2026-09-15", fecha_hasta="2026-12-31"))
    assert respuesta.fechas == [CORTE, date(2026, 10, 31), date(2026, 11, 11)]
    assert len(repo.consultas) == 1
    assert repo.consultas[0]["fechas"] == respuesta.fechas
    futuro = ResultadosEjercicioService(repo).consultar_mensual(ConsultaHistoricoResultados(fecha_desde="2026-12-01", fecha_hasta="2026-12-31"))
    assert futuro.fechas == [] and futuro.datos == []
    assert len(repo.consultas) == 1


def test_mensual_anio_bisiesto_y_limites_del_rango(monkeypatch):
    monkeypatch.setattr('app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.service.fecha_actual_ecuador', lambda: date(2026, 11, 11))
    respuesta = ResultadosEjercicioService(Repositorio({})).consultar_mensual(ConsultaHistoricoResultados(fecha_desde="2024-02-01", fecha_hasta="2024-03-30"))
    assert respuesta.fechas == [date(2024, 2, 29)]


@pytest.mark.parametrize("ruta", ["fecha-corte", "historico-diario", "historico-mensual"])
def test_endpoints_bearer_contratos_y_validacion(ruta, monkeypatch):
    monkeypatch.setattr('app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.service.fecha_actual_ecuador', lambda: date(2026, 11, 11))
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    app.dependency_overrides[get_resultados_ejercicio_service] = lambda: ResultadosEjercicioService(Repositorio())
    client = TestClient(app)
    url = f"/analytic/analisis-contable/resumen-resultados-del-ejercicio/{ruta}"
    body = {"fecha_corte": "2026-09-30"} if ruta == "fecha-corte" else {"fecha_desde": "2026-09-30", "fecha_hasta": "2026-09-30"}
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json=body)
    assert response.status_code == 200
    datos = response.json()
    assert datos["total_registros"] == len(datos["datos"]) == 22
    assert datos["datos"][-1]["saldo"] == "242895.04"
    assert datos["id_agencia_contable"] == datos["neteo"] == 1
    assert client.post(url, json={**body, "id_agencia": 999999}).status_code == 404
    for invalido in ({}, {**body, "neteo": 2}, {**body, "id_agencia": -1}):
        assert client.post(url, json=invalido).status_code == 422
    if ruta != "fecha-corte":
        assert client.post(url, json={**body, "fecha_hasta": "2026-09-29"}).status_code == 422
        if ruta == "historico-diario":
            assert client.post(url, json={**body, "fecha_hasta": "2027-10-01"}).status_code == 422
    else:
        assert client.post(url, json={**body, "fecha_corte": "2026-02-30"}).status_code == 422


def test_diario_hasta_366_dias_no_trunca_resultados():
    desde = date(2024, 1, 1)
    respuesta = ResultadosEjercicioService(Repositorio({})).consultar_diario(ConsultaHistoricoResultados(fecha_desde=desde, fecha_hasta=desde+timedelta(days=365)))
    assert len(respuesta.fechas) == 366
    assert respuesta.total_registros == 366 * 22


def test_historico_mensual_acepta_48_meses_y_rechaza_49(monkeypatch):
    monkeypatch.setattr('app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.service.fecha_actual_ecuador', lambda: date(2026, 11, 11))
    app = FastAPI()
    app.include_router(router, prefix="/analytic")
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    app.dependency_overrides[get_resultados_ejercicio_service] = lambda: ResultadosEjercicioService(Repositorio({}))
    client = TestClient(app)
    url = "/analytic/analisis-contable/resumen-resultados-del-ejercicio/historico-mensual"
    body = {"fecha_desde": "2022-12-01", "fecha_hasta": "2026-11-30"}
    response = client.post(url, json=body)
    assert response.status_code == 200
    assert len(response.json()["fechas"]) == 48
    assert response.json()["total_registros"] == 48 * 22
    assert client.post(url, json={**body, "fecha_desde": "2022-11-01"}).status_code == 422
    assert client.post(url.replace("historico-mensual", "historico-diario"), json=body).status_code == 422
