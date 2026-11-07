from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.ahorro_restringido.control_diario_cancelacion.dependencies import get_cancelacion_restringidos_service
from app.modules.negocios.ahorro_restringido.control_diario_cancelacion.repositories.sql_cancelacion_restringidos_repository import (
    CorteCancelacionRestringidos, SqlCancelacionRestringidosRepository,
)
from app.modules.negocios.ahorro_restringido.control_diario_cancelacion.schemas import (
    ControlCancelacionRestringidosRequest, DetalleCancelacionRestringidosRequest,
)
from app.modules.negocios.ahorro_restringido.control_diario_cancelacion.service import ControlCancelacionRestringidosService

URL = "/negocios/ahorro-restringido/control-diario-cancelacion-restringidos"


def auth():
    return AuthContext.from_token_payload("test", UsuarioTokenPayload(
        sub="test", usuario="Test", id_agencia=2, nombre_agencia="MATRIZ",
        fecha_sistema=date(2026, 11, 6),
    ))


def request(**cambios):
    return ControlCancelacionRestringidosRequest(**{
        "fecha_inicio": "2026-10-01", "fecha_fin": "2026-10-03", **cambios,
    })


def fila(**cambios):
    return dict(id_movimiento=1, numero_cuenta="test-1", numero_cliente="001", nombre_cliente="Cliente de prueba",
                codigo_usuario="ana", nombre_asesor="Ana", cargo="ASESOR", id_agencia=2, agencia="MATRIZ",
                codigo_producto="004", producto_ahorro="Ahorro Meta", fecha_cancelacion=date(2026, 10, 1),
                monto=Decimal("100.10")) | cambios


class Fuente:
    def __init__(self, filas=None):
        self.filas = filas if filas is not None else [
            fila(), fila(id_movimiento=2, numero_cuenta="test-2", monto=Decimal("20.20")),
            fila(id_movimiento=3, numero_cuenta="test-3", codigo_producto="007", producto_ahorro="Taitita",
                 cargo="CAPTADOR", fecha_cancelacion=datetime(2026, 10, 3), monto=Decimal("50.50")),
        ]
        self.calls = []
        self.disponible = True

    def obtener_corte(self, **kwargs):
        self.calls.append(kwargs)
        return CorteCancelacionRestringidos(date(2026, 10, 3), self.filas) if self.disponible else None

    def obtener_nombre_agencia(self, id_agencia):
        return "MATRIZ" if id_agencia == 2 else None


def test_diario_cuentas_y_salida_no_acumulada_con_dias_cero_y_productos_separados():
    fuente = Fuente()
    response = ControlCancelacionRestringidosService(fuente, fuente).obtener(request(), auth())
    assert response.dias == [date(2026, 10, d) for d in (1, 2, 3)]
    assert len(response.filas) == 2
    meta = response.filas[0]
    assert meta.codigo_producto == "004"
    assert [d.monto for d in meta.valores] == [120.30, 0, 0]
    assert [d.cuentas for d in meta.valores] == [2, 0, 0]
    assert response.filas[1].valores[-1].monto == 50.50
    assert fuente.calls[0]["fecha_sistema"] == date(2026, 11, 6)


def test_detalle_conserva_fecha_fin_y_filtra_dia_asesor_cargos_productos_con_totales():
    fuente = Fuente()
    service = ControlCancelacionRestringidosService(fuente, fuente)
    body = DetalleCancelacionRestringidosRequest(**request().model_dump(), fecha="2026-10-03",
                                               codigo_usuario=" ana ", cargos=[" captador ", "CAPTADOR"], productos=["007"])
    response = service.obtener_detalle(body, auth())
    assert response.cargos == ["CAPTADOR"]
    assert response.total_registros == 1
    assert response.total_monto == 50.50
    assert response.items[0].numero_cuenta == "test-3"
    assert fuente.calls[0]["fecha_fin"] == date(2026, 10, 3)
    body.fecha = None
    body.productos = ["004"]
    assert service.obtener_detalle(body, auth()).total_registros == 0


def test_diario_y_detalle_conservan_total_del_mismo_universo_y_cortes_vacios():
    fuente = Fuente()
    service = ControlCancelacionRestringidosService(fuente, fuente)
    diario = service.obtener(request(), auth())
    detalle = service.obtener_detalle(DetalleCancelacionRestringidosRequest(**request().model_dump()), auth())
    assert sum(d.monto for f in diario.filas for d in f.valores) == detalle.total_monto == 170.8
    assert sum(d.cuentas for f in diario.filas for d in f.valores) == detalle.total_registros == 3
    fuente.filas = []
    assert service.obtener(request(), auth()).filas == []
    assert service.obtener_detalle(DetalleCancelacionRestringidosRequest(**request().model_dump()), auth()).total_monto == 0
    fuente.disponible = False
    with pytest.raises(HTTPException) as error:
        service.obtener(request(), auth())
    assert error.value.status_code == 404


@pytest.mark.parametrize("cambios,codigo", [({"fecha_inicio": "2026-11-01", "fecha_fin": "2026-11-07"}, 400), ({"id_agencia": 999}, 404)])
def test_rechaza_futuro_y_agencia_desconocida_antes_de_leer_movimientos(cambios, codigo):
    fuente = Fuente()
    with pytest.raises(HTTPException) as error:
        ControlCancelacionRestringidosService(fuente, fuente).obtener(request(**cambios), auth())
    assert error.value.status_code == codigo
    assert fuente.calls == []


@pytest.mark.parametrize("cambios", [{"fecha_fin": "2026-09-30"}, {"fecha_fin": "2026-11-01"},
                                      {"id_agencia": -1}, {"es_programado": False}, {"fecha_inicio": "0001-01-01"}])
def test_request_rango_y_contrato_estricto(cambios):
    with pytest.raises(ValidationError):
        request(**cambios)


@pytest.mark.parametrize("cambios", [{"fecha": "2026-10-04"}, {"codigo_usuario": " "}, {"cargos": [" "]}, {"productos": [""]}])
def test_detalle_rechaza_filtros_invalidos(cambios):
    with pytest.raises(ValidationError):
        DetalleCancelacionRestringidosRequest(**request().model_dump(), **cambios)


def test_endpoints_bearer_respuestas_y_validaciones():
    client = TestClient(app)
    body = request().model_dump(mode="json")
    for suffix in ("", "/detalle"):
        assert client.post(URL + suffix, json=body).status_code == 401
    fuente = Fuente()
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_cancelacion_restringidos_service] = lambda: ControlCancelacionRestringidosService(fuente, fuente)
    try:
        response = client.post(URL, json=body)
        assert response.status_code == 200
        assert response.json()["filas"][0]["valores"][0] == {"monto": 120.3, "cuentas": 2}
        detalle = client.post(URL + "/detalle", json=body | {"productos": ["004"]})
        assert detalle.status_code == 200
        assert detalle.json()["total_registros"] == 2
        assert detalle.json()["total_monto"] == 120.3
        assert client.post(URL, json=body | {"id_agencia": -1}).status_code == 422
    finally:
        app.dependency_overrides.clear()


class DB:
    def __init__(self, corte):
        self.corte = corte
        self.calls = []

    def execute(self, query, params):
        self.calls.append((str(query), params))
        return self

    def mappings(self):
        return self

    def first(self):
        return self.corte

    def all(self):
        return [fila()]


@pytest.mark.parametrize("en_linea", [False, True])
def test_sql_cierre_programado_salida_saldo_sin_duplicar_interes_y_reversos(en_linea):
    fecha = date(2026, 11, 6) if en_linea else date(2026, 10, 31)
    db = DB({"fecha": datetime.combine(fecha, datetime.min.time()), "cerrado": not en_linea,
             "cierre": datetime(2026, 11, 1, 3)})
    corte = SqlCancelacionRestringidosRepository(db).obtener_corte(
        fecha_inicio=fecha.replace(day=1), fecha_fin=fecha, id_agencia=2, fecha_sistema=date(2026, 11, 6))
    assert corte.fecha == fecha
    query, params = db.calls[1]
    assert params["transaccion_cierre"] == 30
    assert params["es_programado"] is True
    assert params["estado_cerrado"] == "C"
    assert params["id_agencia"] == 2
    assert "I.SUMASALDO = 1" in query and "SUM(IM.VALOR)" in query
    assert "MD.DEBITO = 1" in query
    assert "CM.CODIGOESTADOCUENTA =" not in query
    assert "MR.FECHASISTEMA < :corte_exclusivo" in query and "MT.ESREVERSO = 0" in query
    assert "PARTITION BY S.NUMEROCUENTA" in query and "WHERE S.orden = 1" in query
    assert query.count("FOR SYSTEM_TIME AS OF :cierre") == (0 if en_linea else 2)


@pytest.mark.parametrize("corte", [None, {"fecha": date(2026, 10, 31), "cerrado": True, "cierre": None}])
def test_sin_cierre_no_usa_saldos_actuales(corte):
    db = DB(corte)
    assert SqlCancelacionRestringidosRepository(db).obtener_corte(
        fecha_inicio=date(2026, 10, 1), fecha_fin=date(2026, 10, 31), id_agencia=0,
        fecha_sistema=date(2026, 11, 6)) is None
    assert len(db.calls) == 1
