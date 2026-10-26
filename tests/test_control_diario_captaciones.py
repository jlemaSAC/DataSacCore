from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.dependencies import (
    get_control_diario_captaciones_service,
)
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.repositories.sql_control_diario_captaciones_repository import (
    CorteCaptaciones,
    SqlControlDiarioCaptacionesRepository,
)
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.schemas import (
    ControlDiarioCaptacionesRequest,
    DetalleControlCaptacionesRequest,
)
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.service import ControlDiarioCaptacionesService


URL = "/negocios/depositos-a-plazos/control-diario-captaciones"


def auth():
    return AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="Test", id_agencia=2, nombre_agencia="MATRIZ",
        fecha_sistema=date(2026, 10, 21),
    ))


def request(**cambios):
    return ControlDiarioCaptacionesRequest(**{
        "fecha_inicio": "2026-10-10", "fecha_fin": "2026-10-12", "id_agencia": 2,
        **cambios,
    })


def fila(**cambios):
    return {
        "codigo": "ana", "nombre": "Ana", "cargo": "CAPTADOR", "IDAGENCIA": 2,
        "agencia": "MATRIZ", "fecha": date(2026, 10, 10), "condicion": "NUEVO",
        "monto": Decimal("100.10"), **cambios,
    }


class Fuente:
    def __init__(self, filas=None, fecha=date(2026, 10, 12)):
        self.corte = CorteCaptaciones(fecha, filas if filas is not None else [
            fila(), fila(condicion="RENOVADO", monto=Decimal("50.20")),
            fila(fecha=date(2026, 10, 12), monto=Decimal("10.30")),
        ])
        self.calls = []

    def obtener_diario(self, **kwargs):
        self.calls.append(kwargs)
        return self.corte

    def obtener_nombre_agencia(self, id_agencia):
        return "MATRIZ" if id_agencia == 2 else None


def test_pivota_montos_diarios_por_condicion_sin_acumular_y_completa_dias_con_cero():
    fuente = Fuente()
    respuesta = ControlDiarioCaptacionesService(fuente, fuente).obtener(request(), auth())
    assert respuesta.dias == [date(2026, 10, 10), date(2026, 10, 11), date(2026, 10, 12)]
    assert [d.model_dump() for d in respuesta.filas[0].valores] == [
        {"nuevo": 100.10, "renovado": 50.20},
        {"nuevo": 0, "renovado": 0},
        {"nuevo": 10.30, "renovado": 0},
    ]
    assert fuente.calls == [{
        "fecha_inicio": date(2026, 10, 10), "fecha_fin": date(2026, 10, 12),
        "id_agencia": 2, "fecha_sistema": date(2026, 10, 21),
    }]


def test_no_mezcla_captadores_con_mismo_nombre_o_codigo_en_otras_agencias():
    fuente = Fuente([fila(), fila(codigo="otro"), fila(IDAGENCIA=3, agencia="SUR")])
    respuesta = ControlDiarioCaptacionesService(fuente, fuente).obtener(request(id_agencia=0), auth())
    assert len(respuesta.filas) == 3
    assert sum(f.valores[0].nuevo for f in respuesta.filas) == pytest.approx(300.30)
    assert {(f.codigo_usuario, f.id_agencia) for f in respuesta.filas} == {("ana", 2), ("otro", 2), ("ana", 3)}


def test_suma_decimal_y_respeta_limites_inclusivos_y_corte_real():
    fuente = Fuente([
        fila(monto=Decimal("0.10")), fila(monto=Decimal("0.20")),
        fila(fecha=date(2026, 10, 9)), fila(fecha=date(2026, 10, 13)),
    ], fecha=date(2026, 10, 11))
    respuesta = ControlDiarioCaptacionesService(fuente, fuente).obtener(request(), auth())
    assert respuesta.fecha_corte == date(2026, 10, 11)
    assert respuesta.filas[0].valores[0].nuevo == 0.3
    assert respuesta.filas[0].valores[-1].nuevo == 0


def test_un_dia_y_corte_vacio_conserva_el_calendario():
    fuente = Fuente([])
    respuesta = ControlDiarioCaptacionesService(fuente, fuente).obtener(request(fecha_fin="2026-10-10"), auth())
    assert respuesta.dias == [date(2026, 10, 10)]
    assert respuesta.filas == []


@pytest.mark.parametrize("cambios", [
    {"fecha_inicio": "2026-10-13"}, {"fecha_inicio": "2026-09-30"},
    {"id_agencia": -1}, {"cargo": "CAPTADOR"}, {"fecha_fin": "9999-12-31"},
])
def test_valida_rango_mismo_mes_y_contrato_estricto(cambios):
    with pytest.raises(ValidationError):
        request(**cambios)


@pytest.mark.parametrize("cambios,codigo", [({"fecha_fin": "2026-10-22"}, 400), ({"id_agencia": 99}, 404)])
def test_fecha_futura_y_agencia_desconocida_no_consultan_depositos(cambios, codigo):
    fuente = Fuente()
    with pytest.raises(HTTPException) as error:
        ControlDiarioCaptacionesService(fuente, fuente).obtener(request(**cambios), auth())
    assert error.value.status_code == codigo
    assert fuente.calls == []


def test_distingue_corte_faltante_de_cero_captaciones():
    fuente = Fuente()
    fuente.corte = None
    with pytest.raises(HTTPException) as error:
        ControlDiarioCaptacionesService(fuente, fuente).obtener(request(), auth())
    assert error.value.status_code == 404


def test_endpoint_bearer_contrato_y_validacion():
    client = TestClient(app)
    body = request().model_dump(mode="json")
    assert client.post(URL, json=body).status_code == 401
    fuente = Fuente()
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_control_diario_captaciones_service] = lambda: ControlDiarioCaptacionesService(fuente, fuente)
    try:
        response = client.post(URL, json=body)
        assert response.status_code == 200
        datos = response.json()
        assert datos["dias"] == ["2026-10-10", "2026-10-11", "2026-10-12"]
        assert datos["filas"][0]["valores"][0] == {"nuevo": 100.1, "renovado": 50.2}
        assert client.post(URL, json={**body, "fecha_inicio": "2026-09-30"}).status_code == 422
    finally:
        app.dependency_overrides.clear()


class Resultado:
    def __init__(self, row=None, rows=None):
        self.row, self.rows = row, rows or []

    def mappings(self):
        return self

    def first(self):
        return self.row

    def all(self):
        return self.rows


class SessionFake:
    def __init__(self, corte):
        self.corte, self.calls = corte, []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return Resultado(row=self.corte) if len(self.calls) == 1 else Resultado(rows=[fila()])


@pytest.mark.parametrize("fecha,en_linea", [(date(2026, 10, 21), True), (date(2026, 10, 20), False)])
def test_repositorio_usa_solo_fecha_de_creacion_sin_filtrar_estado_ni_cliente(fecha, en_linea):
    db = SessionFake({"fecha": fecha, "cierre": datetime(2026, 10, 21, 2, 59)})
    respuesta = SqlControlDiarioCaptacionesRepository(db).obtener_diario(
        fecha_inicio=date(2026, 10, 10), fecha_fin=fecha,
        fecha_sistema=date(2026, 10, 21), id_agencia=2,
    )
    sql, params = db.calls[1]
    assert ("FOR SYSTEM_TIME AS OF :cierre" in sql) is not en_linea
    assert "D.CODIGOESTADODEPOSITO IN" not in sql
    assert "D.CODIGOESTADODEPOSITO NOT IN" not in sql
    assert "DC.ESPRINCIPAL" not in sql
    assert "R.IDDEPOSITODESTINO = D.ID" in sql
    assert "R.FECHA >= :inicio_mes AND R.FECHA < :corte_exclusivo" in sql
    assert "D.FECHACREACION >= :fecha_inicio" in sql
    assert "D.FECHACREACION < :hasta_exclusivo" in sql
    assert params["id_agencia"] == 2
    assert params["inicio_mes"] == date(2026, 10, 1)
    assert params["hasta_exclusivo"].day == fecha.day + 1
    assert respuesta.fecha == fecha


@pytest.mark.parametrize("corte", [None, {"fecha": date(2026, 10, 20), "cierre": None}])
def test_repositorio_no_sustituye_historicos_faltantes_por_datos_actuales(corte):
    db = SessionFake(corte)
    assert SqlControlDiarioCaptacionesRepository(db).obtener_diario(
        fecha_inicio=date(2026, 10, 10), fecha_fin=date(2026, 10, 20),
        fecha_sistema=date(2026, 10, 21), id_agencia=0,
    ) is None
    assert len(db.calls) == 1


def detalle_request(**cambios):
    return DetalleControlCaptacionesRequest(**{
        **request().model_dump(), "fecha": date(2026, 10, 10),
        "codigo_usuario": "ana", "cargos": [" captador "], "condicion": "renovado",
        **cambios,
    })


def deposito(**cambios):
    return {
        "id_deposito": 1, "numero_cliente": 123, "nombre_cliente": "Cliente de prueba",
        "agencia": "MATRIZ", "captador": "Ana", "numero_deposito": "DPF-001",
        "monto": Decimal("100.10"), "interes_total": Decimal("0.10"),
        "tasa_total": Decimal("7.25"),
        "tiene_prestamo": True, "fecha_vencimiento": date(2027, 1, 10), "estado": "ACTIVO",
        **cambios,
    }


class FuenteDetalle(Fuente):
    def __init__(self, filas=None):
        super().__init__()
        self.corte = CorteCaptaciones(date(2026, 10, 12), filas if filas is not None else [deposito()])

    def obtener_detalle(self, **kwargs):
        self.calls.append(kwargs)
        return self.corte


def test_detalle_conserva_corte_original_filtros_total_decimal_y_tasa():
    fuente = FuenteDetalle([deposito(), deposito(id_deposito=2, interes_total=Decimal("0.20"))])
    respuesta = ControlDiarioCaptacionesService(fuente, fuente).obtener_detalle(detalle_request(), auth())
    assert fuente.calls[0]["fecha_fin"] == date(2026, 10, 12)
    assert fuente.calls[0]["fecha"] == date(2026, 10, 10)
    assert fuente.calls[0]["cargos"] == ["CAPTADOR"]
    assert fuente.calls[0]["condicion"] == "renovado"
    assert respuesta.fecha_corte == date(2026, 10, 12)
    assert respuesta.total_monto == 200.2
    assert respuesta.total_interes == 0.3
    assert respuesta.items[0].numero_cliente == "123"
    assert respuesta.items[0].tasa_total == 7.25


def test_detalle_devuelve_mas_de_500_depositos_sin_paginacion():
    fuente = FuenteDetalle([deposito(id_deposito=i) for i in range(601)])
    respuesta = ControlDiarioCaptacionesService(fuente, fuente).obtener_detalle(detalle_request(fecha=None), auth())
    assert respuesta.total_registros == len(respuesta.items) == 601
    assert respuesta.total_monto == 60160.1
    assert respuesta.total_interes == 60.1
    assert not {"pagina", "tamano_pagina"} & respuesta.model_dump().keys()


def test_detalle_vacio_y_corte_no_disponible():
    fuente = FuenteDetalle([])
    servicio = ControlDiarioCaptacionesService(fuente, fuente)
    respuesta = servicio.obtener_detalle(detalle_request(), auth())
    assert respuesta.items == []
    assert respuesta.total_monto == respuesta.total_interes == 0
    fuente.corte = None
    with pytest.raises(HTTPException) as error:
        servicio.obtener_detalle(detalle_request(), auth())
    assert error.value.status_code == 404


@pytest.mark.parametrize("cambios", [
    {"fecha": "2026-10-09"}, {"fecha": "2026-10-13"}, {"condicion": "invalida"},
    {"codigo_usuario": " "}, {"cargos": [""]}, {"pagina": 1},
])
def test_detalle_rechaza_dia_fuera_del_rango_y_filtros_invalidos(cambios):
    with pytest.raises(ValidationError):
        detalle_request(**cambios)


@pytest.mark.parametrize("cambios,codigo", [({"fecha_fin": "2026-10-22"}, 400), ({"id_agencia": 999}, 404)])
def test_detalle_valida_fecha_del_sistema_y_agencia(cambios, codigo):
    fuente = FuenteDetalle()
    with pytest.raises(HTTPException) as error:
        ControlDiarioCaptacionesService(fuente, fuente).obtener_detalle(detalle_request(**cambios), auth())
    assert error.value.status_code == codigo
    assert fuente.calls == []


def test_endpoint_detalle_bearer_contrato_completo_con_tasa_sin_paginacion():
    client = TestClient(app)
    body = detalle_request().model_dump(mode="json")
    assert client.post(URL + "/detalle", json=body).status_code == 401
    fuente = FuenteDetalle()
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_control_diario_captaciones_service] = lambda: ControlDiarioCaptacionesService(fuente, fuente)
    try:
        respuesta = client.post(URL + "/detalle", json=body)
        assert respuesta.status_code == 200
        assert respuesta.json()["total_registros"] == 1
        assert len(respuesta.json()["items"][0]) == 12
        assert respuesta.json()["items"][0]["tasa_total"] == 7.25
        assert client.post(URL + "/detalle", json={**body, "fecha": "2026-10-13"}).status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("en_linea", [True, False])
def test_detalle_sql_comparte_universo_y_usa_intereses_y_prestamos_del_corte(en_linea):
    fecha = date(2026, 10, 21 if en_linea else 20)
    db = SessionFake({"fecha": fecha, "cierre": datetime(2026, 10, 21, 2),
                      "cierre_colocacion": datetime(2026, 10, 21, 3)})
    SqlControlDiarioCaptacionesRepository(db).obtener_detalle(
        fecha_inicio=date(2026, 10, 10), fecha_fin=fecha, fecha_sistema=date(2026, 10, 21),
        id_agencia=2, fecha=date(2026, 10, 10), codigo_usuario="ana", cargos=["CAPTADOR"], condicion="renovado",
    )
    sql, params = db.calls[1]
    assert ("INVERSION.DEPOSITO_ITEMPLAZO FOR SYSTEM_TIME AS OF :cierre" in sql) is not en_linea
    assert ("COLOCACION.PRESTAMO FOR SYSTEM_TIME AS OF :cierre_colocacion" in sql) is not en_linea
    assert "IP.IDDEPOSITO = X.ID AND IP.IDITEMPLAZO = 2" in sql
    assert "OUTER APPLY" in sql
    assert "Cliente.id_cliente IS NULL THEN NULL" in sql
    assert "AS numero_cliente" in sql and "SIN DATOS" in sql
    assert "IP.IDITEMPLAZO = 2" in sql
    assert "X.fecha = :fecha" in sql
    assert "X.codigo = :codigo_usuario" in sql
    assert "X.condicion = :condicion" in sql
    assert "IN (:cargo_0)" in sql
    assert params["hasta_exclusivo"].day == fecha.day + 1
    assert params["fecha"] == date(2026, 10, 10)
    assert params["condicion"] == "RENOVADO"
    assert "OFFSET" not in sql and "FETCH NEXT" not in sql
    assert "D.TASA + D.VARIACION_TASA" in sql
    assert "X.tasa_total" in sql


def test_detalle_historico_sin_cierre_de_colocacion_no_usa_prestamos_actuales():
    db = SessionFake({"fecha": date(2026, 10, 20), "cierre": datetime(2026, 10, 21, 2)})
    assert SqlControlDiarioCaptacionesRepository(db).obtener_detalle(
        fecha_inicio=date(2026, 10, 10), fecha_fin=date(2026, 10, 20), fecha_sistema=date(2026, 10, 21),
        id_agencia=0, fecha=None, codigo_usuario=None, cargos=[], condicion="todas",
    ) is None
    assert len(db.calls) == 1


def test_endpoint_detalle_incluye_deposito_cancelado_y_cliente_no_disponible():
    fuente = FuenteDetalle([
        deposito(estado="Cancelado", monto=Decimal("13765.91")),
        deposito(id_deposito=2, numero_cliente="SIN DATOS", nombre_cliente="SIN DATOS",
                 tiene_prestamo=None, estado="Anulado"),
    ])
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_control_diario_captaciones_service] = lambda: ControlDiarioCaptacionesService(fuente, fuente)
    try:
        response = TestClient(app).post(URL + "/detalle", json=detalle_request(fecha=None).model_dump(mode="json"))
        assert response.status_code == 200
        datos = response.json()
        assert datos["total_monto"] == 13866.01
        assert [item["estado"] for item in datos["items"]] == ["Cancelado", "Anulado"]
        assert datos["items"][1]["numero_cliente"] == "SIN DATOS"
        assert datos["items"][1]["tiene_prestamo"] is None
    finally:
        app.dependency_overrides.clear()
