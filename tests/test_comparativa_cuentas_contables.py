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
