from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.ahorro_restringido.control_vencimiento_restringido.dependencies import get_control_vencimiento_restringido_service
from app.modules.negocios.ahorro_restringido.control_vencimiento_restringido.repositories.sql_control_vencimiento_restringido_repository import DetalleVencimientoRestringidoResultado, SqlControlVencimientoRestringidoRepository
from app.modules.negocios.ahorro_restringido.control_vencimiento_restringido.schemas import ControlVencimientoRestringidoRequest, DetalleControlVencimientoRestringidoRequest
from app.modules.negocios.ahorro_restringido.control_vencimiento_restringido.service import ControlVencimientoRestringidoService


def auth():
    return AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="Test", id_agencia=2, nombre_agencia="MATRIZ",
        fecha_sistema=date(2026, 10, 23),
    ))


def fila(codigo="ana", agencia=2, saldo="0.10", producto="004"):
    return dict(codigo=codigo, IDAGENCIA=agencia, agencia=f"AGENCIA {agencia}",
                nombre=codigo, cargo="CAPTADOR", saldo=Decimal(saldo),
                codigo_producto=producto, producto_ahorro="Ahorro Meta")


class Fuente:
    def __init__(self, filas=None):
        self.filas = filas if filas is not None else [fila(), fila("bea", saldo="0.20"), fila(agencia=17, saldo="100.34")]
        self.calls = []
        self.agencias_gerentes = []

    def obtener_saldos(self, **kwargs):
        self.calls.append(kwargs)
        return self.filas

    def obtener_nombre_agencia(self, id_agencia):
        return "MATRIZ" if id_agencia == 2 else None

    def obtener_gerentes_oficina(self, agencias):
        self.agencias_gerentes = agencias
        return [{"Agencia": agencia, "GerenteOficina": "Responsable"} for agencia in agencias]


def request(**kwargs):
    return ControlVencimientoRestringidoRequest(fecha_inicio="2026-10-23", fecha_fin="2026-11-30", **kwargs)


def test_acumula_saldo_exacto_y_conserva_codigo_repetido_en_dos_agencias():
    fuente = Fuente()
    respuesta = ControlVencimientoRestringidoService(fuente, fuente).obtener(request(), auth())
    assert respuesta.saldo_total == 100.64
    assert len(respuesta.filas) == 3
    assert {fila.clave for fila in respuesta.filas} == {"ana::2::004", "bea::2::004", "ana::17::004"}
    assert fuente.agencias_gerentes == ["AGENCIA 17", "AGENCIA 2"]
    assert respuesta.fecha_sistema == date(2026, 10, 23)


def test_rango_futuro_de_varios_meses_y_agencia_se_delegan_a_la_consulta():
    fuente = Fuente()
    body = ControlVencimientoRestringidoRequest(fecha_inicio="2026-12-20", fecha_fin="2027-02-15", id_agencia=2)
    ControlVencimientoRestringidoService(fuente, fuente).obtener(body, auth())
    assert fuente.calls == [dict(fecha_inicio=date(2026, 12, 20), fecha_fin=date(2027, 2, 15), id_agencia=2)]


def test_agencia_inexistente_se_rechaza_antes_de_consultar_depositos():
    fuente = Fuente()
    with pytest.raises(HTTPException) as error:
        ControlVencimientoRestringidoService(fuente, fuente).obtener(request(id_agencia=99), auth())
    assert error.value.status_code == 404
    assert fuente.calls == []


def test_sin_vencimientos_devuelve_cero_y_lista_vacia():
    fuente = Fuente([])
    resultado = ControlVencimientoRestringidoService(fuente, fuente).obtener(request(), auth())
    assert resultado.saldo_total == 0
    assert resultado.filas == []
    assert resultado.agencias_gerentes_oficina == []


@pytest.mark.parametrize("inicio,fin", [("2026-11-01", "2026-10-31"), ("2026-10-01", "9999-12-31")])
def test_valida_orden_y_limite_superior_del_rango(inicio, fin):
    with pytest.raises(ValidationError):
        ControlVencimientoRestringidoRequest(fecha_inicio=inicio, fecha_fin=fin)


def test_endpoint_bearer_contrato_sin_variaciones_y_filtros_obligatorios():
    client = TestClient(app)
    url = "/negocios/ahorro-restringido/control-vencimiento-restringido"
    body = request().model_dump(mode="json")
    assert client.post(url, json=body).status_code == 401
    fuente = Fuente()
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_control_vencimiento_restringido_service] = lambda: ControlVencimientoRestringidoService(fuente, fuente)
    try:
        response = client.post(url, json=body)
        assert response.status_code == 200
        datos = response.json()
        assert datos["saldo_total"] == 100.64
        assert datos["fecha_fin"] == "2026-11-30"
        assert set(datos["filas"][0]) == {
            "Clave", "CodigoUsuario", "NombreAsesor", "Cargo", "CodigoProducto", "ProductoAhorro", "IdAgencia", "Agencia", "Saldo",
        }
        assert set(datos) == {
            "fecha_inicio", "fecha_fin", "id_agencia", "fecha_sistema", "saldo_total", "filas", "agencias_gerentes_oficina",
        }
        assert client.post(url, json={**body, "fecha_fin": "2026-10-22"}).status_code == 422
        assert client.post(url, json={"id_agencia": 0}).status_code == 422
        assert client.post(url, json={**body, "id_agencia": -1}).status_code == 422
        assert client.post(url, json={**body, "filtrar_diferidos": True}).status_code == 422
    finally:
        app.dependency_overrides.clear()


class Resultado:
    def mappings(self):
        return self

    def all(self):
        return [fila(saldo="123.45")]


class SessionFake:
    def __init__(self):
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return Resultado()


@pytest.mark.parametrize("inicio,fin,hasta", [
    (date(2026, 10, 23), date(2026, 10, 23), date(2026, 10, 24)),
    (date(2026, 12, 20), date(2026, 12, 31), date(2027, 1, 1)),
])
def test_consulta_incluye_todo_el_dia_fin_y_conserva_importes_decimal(inicio, fin, hasta):
    db = SessionFake()
    filas = SqlControlVencimientoRestringidoRepository(db).obtener_saldos(fecha_inicio=inicio, fecha_fin=fin, id_agencia=2)
    sql, params = db.calls[0]
    assert params == {"fecha_inicio": inicio, "hasta_exclusivo": hasta, "id_agencia": 2, "es_programado": True}
    assert "CP.FECHAVENCIMIENTO >= :fecha_inicio" in sql
    assert "CP.FECHAVENCIMIENTO < :hasta_exclusivo" in sql
    assert "CU.IDAGENCIA = :id_agencia" in sql
    assert filas[0]["saldo"] == Decimal("123.45")


def test_consulta_consolidada_no_restringe_por_agencia():
    db = SessionFake()
    SqlControlVencimientoRestringidoRepository(db).obtener_saldos(fecha_inicio=date(2026, 10, 23), fecha_fin=date(2026, 11, 30), id_agencia=0)
    assert "CU.IDAGENCIA = :id_agencia" not in db.calls[0][0]


def item_detalle():
    return dict(
        id_programacion=10, numero_cliente=123, nombre_cliente="CLIENTE PRUEBA",
        agencia="MATRIZ", asesor="ANA", numero_cuenta="CUENTA-001", producto_ahorro="Ahorro Meta",
        saldo_actual=Decimal("3000.00"), tasa=Decimal("7.25"),
        tiene_prestamo=True, fecha_vencimiento=date(2026, 11, 30), estado="Activo",
    )


class FuenteDetalle(Fuente):
    def obtener_detalle(self, **kwargs):
        self.calls.append(kwargs)
        return DetalleVencimientoRestringidoResultado(120, Decimal("6000"), [item_detalle()])


def test_detalle_conserva_agencia_asesor_productos_y_totales_de_todo_el_filtro():
    fuente = FuenteDetalle()
    body = DetalleControlVencimientoRestringidoRequest(**request(id_agencia=2).model_dump(),
        codigo_usuario=" ana ", productos=[" 004 ", "004"], pagina=2, tamano_pagina=50)
    respuesta = ControlVencimientoRestringidoService(fuente, fuente).obtener_detalle(body)
    assert fuente.calls == [body.model_dump()]
    assert respuesta.codigo_usuario == "ana"
    assert respuesta.productos == ["004"]
    assert respuesta.total_saldo == 6000
    assert respuesta.total_registros == 120
    assert respuesta.items[0].numero_cliente == "123"
    assert respuesta.items[0].tasa == 7.25
    assert respuesta.items[0].tiene_prestamo is True


def test_detalle_sin_paginacion_devuelve_todos_y_omite_la_pagina():
    fuente = FuenteDetalle()
    body = DetalleControlVencimientoRestringidoRequest(**request().model_dump(), sin_paginacion=True)
    respuesta = ControlVencimientoRestringidoService(fuente, fuente).obtener_detalle(body)

    assert fuente.calls == [body.model_dump()]
    assert respuesta.pagina is None
    assert respuesta.tamano_pagina is None
    assert respuesta.total_registros == 120


@pytest.mark.parametrize("campos", [
    {"pagina": 0}, {"tamano_pagina": 0}, {"tamano_pagina": 501},
    {"codigo_usuario": " "}, {"productos": [" "]},
])
def test_detalle_valida_paginacion_y_filtros(campos):
    with pytest.raises(ValidationError):
        DetalleControlVencimientoRestringidoRequest(**request().model_dump(), **campos)


def test_endpoint_detalle_requiere_bearer_y_devuelve_campos_solicitados():
    url = "/negocios/ahorro-restringido/control-vencimiento-restringido/detalle"
    client = TestClient(app)
    body = {**request().model_dump(mode="json"), "codigo_usuario": "ana", "productos": ["004"]}
    assert client.post(url, json=body).status_code == 401
    fuente = FuenteDetalle()
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_control_vencimiento_restringido_service] = lambda: ControlVencimientoRestringidoService(fuente, fuente)
    try:
        respuesta = client.post(url, json=body)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert set(datos["items"][0]) == {
            "id_programacion", "numero_cliente", "nombre_cliente", "agencia", "asesor", "numero_cuenta",
            "saldo_actual", "producto_ahorro", "tasa", "tiene_prestamo", "fecha_vencimiento", "estado",
        }
        assert datos["items"][0]["fecha_vencimiento"] == "2026-11-30"
        assert datos["total_registros"] == 120
        assert client.post(url, json={**body, "id_agencia": 99}).status_code == 404
        assert client.post(url, json={**body, "tamano_pagina": 501}).status_code == 422
    finally:
        app.dependency_overrides.clear()


class ResultadoDetalle:
    def __init__(self, total):
        self.total = total

    def mappings(self):
        return self

    def first(self):
        return dict(total_registros=self.total, total_saldo=Decimal("6000.00"))

    def all(self):
        return [item_detalle()]


class SessionDetalle:
    def __init__(self, total=120):
        self.total, self.calls = total, []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return ResultadoDetalle(self.total)


def test_consulta_detalle_parametriza_filtros_y_conserva_el_universo_del_resumen():
    db = SessionDetalle()
    producto = "004'); SELECT 1; --"
    resultado = SqlControlVencimientoRestringidoRepository(db).obtener_detalle(
        fecha_inicio=date(2026, 10, 23), fecha_fin=date(2026, 11, 30), id_agencia=2,
        codigo_usuario="ana", productos=[producto], pagina=2, tamano_pagina=50,
    )
    assert len(db.calls) == 2
    for sql, params in db.calls:
        assert producto not in sql
        assert params["producto_0"] == producto
        assert params["codigo_usuario"] == "ana"
        assert params["hasta_exclusivo"] == date(2026, 12, 1)
        assert params["es_programado"] is True
        assert "CP.ACTIVO = 1" in sql
        assert "CU.CODIGOESTADO IN (N'A', N'I', N'B')" in sql
        assert "I.SUMASALDO = 1" in sql
        assert "SUM(CI.SALDO)" in sql
        assert "WHERE X.CODIGOTIPOCUENTA IN (:producto_0)" in sql
        assert "FOR SYSTEM_TIME" not in sql
    assert db.calls[1][1]["offset"] == 50
    assert db.calls[1][1]["tamano_pagina"] == 50
    assert resultado.total_saldo == Decimal("6000.00")
    assert resultado.items[0]["saldo_actual"] == Decimal("3000.00")


def test_detalle_sin_paginacion_consulta_todas_las_filas_sin_offset():
    db = SessionDetalle(total=120)
    resultado = SqlControlVencimientoRestringidoRepository(db).obtener_detalle(
        fecha_inicio=date(2026, 10, 23), fecha_fin=date(2026, 11, 30), id_agencia=0,
        codigo_usuario=None, productos=[], pagina=1, tamano_pagina=100, sin_paginacion=True,
    )

    assert len(db.calls) == 2
    sql, params = db.calls[1]
    assert "OFFSET" not in sql
    assert "FETCH NEXT" not in sql
    assert "offset" not in params
    assert "tamano_pagina" not in params
    assert resultado.total_registros == 120


@pytest.mark.parametrize("total,pagina", [(0, 1), (120, 4)])
def test_detalle_vacio_o_pagina_fuera_del_resultado_no_solicita_filas_adicionales(total, pagina):
    db = SessionDetalle(total)
    resultado = SqlControlVencimientoRestringidoRepository(db).obtener_detalle(
        fecha_inicio=date(2026, 10, 23), fecha_fin=date(2026, 11, 30), id_agencia=0,
        codigo_usuario=None, productos=[], pagina=pagina, tamano_pagina=50,
    )
    assert len(db.calls) == 1
    assert resultado.items == []
    assert resultado.total_registros == total


def test_conserva_productos_distintos_del_mismo_asesor_y_agencia():
    fuente = Fuente([fila(saldo="10.25", producto="004"), fila(saldo="20.30", producto="007")])
    respuesta = ControlVencimientoRestringidoService(fuente, fuente).obtener(request(), auth())
    assert respuesta.saldo_total == 30.55
    assert {fila.clave for fila in respuesta.filas} == {"ana::2::004", "ana::2::007"}
    assert {fila.codigo_producto for fila in respuesta.filas} == {"004", "007"}
