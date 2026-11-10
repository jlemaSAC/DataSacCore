from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.contabilidad.saldos_diarios.dependencies import get_saldos_diarios_service
from app.modules.contabilidad.saldos_diarios.router import router
from app.modules.contabilidad.saldos_diarios.schemas import ConsultaSaldosDiarios
from app.modules.contabilidad.saldos_diarios.service import SaldosDiariosService


class Repositorio:
    def __init__(self):
        self.argumentos = None

    def obtener_empresa_agencia(self, agencia):
        return 1 if agencia in (1, 2) else None

    def obtener_cuentas_activas(self, empresa):
        return [{"codigo_cuenta": "1", "nombre_cuenta": "ACTIVO"},
                {"codigo_cuenta": "2", "nombre_cuenta": "PASIVO"}]

    def obtener_saldos(self, **kwargs):
        self.argumentos = kwargs
        return [dict(fecha=date(2026, 10, 1), codigo_cuenta="1", saldo=Decimal("100.00")),
                dict(fecha=date(2026, 10, 1), codigo_cuenta="1908", saldo=Decimal("20.00"))]


def test_servicio_consolida_y_devuelve_todos_los_registros():
    repo = Repositorio()
    consulta = ConsultaSaldosDiarios(fecha_desde="2026-10-01", fecha_hasta="2026-10-02",
                                    id_agencia=0, neteo=1)
    respuesta = SaldosDiariosService(repo).consultar(consulta)
    assert respuesta.id_agencia_contable == 1
    assert respuesta.total_registros == 1
    assert repo.argumentos["id_agencia"] == 1
    assert "offset" not in repo.argumentos
    assert "limite" not in repo.argumentos
    assert respuesta.datos[0].saldo == Decimal("80.00")
    assert respuesta.datos[0].codigo_cuenta == "1"


def test_neteo_con_saldo_cero_y_cuenta_de_ajuste_ausente():
    class Repo(Repositorio):
        def obtener_saldos(self, **kwargs):
            return [{"fecha": date(2026, 10, 1), "codigo_cuenta": "1", "saldo": Decimal("0.00")}]

    consulta = ConsultaSaldosDiarios(fecha_desde="2026-10-01", fecha_hasta="2026-10-01", id_agencia=0, neteo=1)
    resultado = SaldosDiariosService(Repo()).consultar(consulta)
    assert resultado.datos[0].saldo == Decimal("0.00")
    assert resultado.total_registros == 1


def test_conserva_saldo_cero_resultante_del_neteo():
    class Repo(Repositorio):
        def obtener_saldos(self, **kwargs):
            return [
                {"fecha": date(2026, 10, 1), "codigo_cuenta": "1", "saldo": Decimal("20.00")},
                {"fecha": date(2026, 10, 1), "codigo_cuenta": "1908", "saldo": Decimal("20.00")},
            ]

    consulta = ConsultaSaldosDiarios(fecha_desde="2026-10-01", fecha_hasta="2026-10-01", id_agencia=0, neteo=1)
    resultado = SaldosDiariosService(Repo()).consultar(consulta)
    assert resultado.total_registros == 1
    assert resultado.datos[0].saldo == Decimal("0.00")


def test_endpoint_devuelve_mas_de_mil_registros():
    class RepositorioGrande(Repositorio):
        def obtener_cuentas_activas(self, empresa):
            return super().obtener_cuentas_activas(empresa) * 1001

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    app.dependency_overrides[get_saldos_diarios_service] = lambda: SaldosDiariosService(RepositorioGrande())
    response = TestClient(app).post("/contabilidad/saldos-diarios", json={
        "fecha_desde": "2026-10-01", "fecha_hasta": "2026-10-01", "id_agencia": 0,
    })
    assert response.status_code == 200
    assert response.json()["total_registros"] == len(response.json()["datos"]) == 1001


def test_endpoint_validacion_y_autenticacion():
    app = FastAPI()
    app.include_router(router)
    repo = Repositorio()
    app.dependency_overrides[get_saldos_diarios_service] = lambda: SaldosDiariosService(repo)
    client = TestClient(app)
    url = "/contabilidad/saldos-diarios"
    body = {"fecha_desde": "2026-10-01", "fecha_hasta": "2026-10-01", "id_agencia": 2, "neteo": 0}
    assert client.post(url, json=body).status_code == 401
    app.dependency_overrides[get_current_auth_context] = lambda: object()
    response = client.post(url, json=body)
    assert response.status_code == 200
    assert response.json()["id_agencia_contable"] == 2
    assert response.json()["total_registros"] == 1
    assert response.json()["datos"] == [
        {"fecha": "2026-10-01", "codigo_cuenta": "1", "nombre_cuenta": "ACTIVO", "saldo": "100.00"},
    ]
    assert "pagina" not in response.json()
    assert "tamanio_pagina" not in response.json()
    assert "total_paginas" not in response.json()
    assert client.post(url, json={**body, "fecha_hasta": "2026-09-30"}).status_code == 422
    assert client.post(url, json={**body, "id_agencia": -1}).status_code == 422
    assert client.post(url, json={**body, "neteo": 2}).status_code == 422
    assert client.post(url, json={**body, "id_agencia": 999}).status_code == 404
    assert client.post(url, json={**body, "fecha_hasta": "2027-10-03"}).status_code == 422
