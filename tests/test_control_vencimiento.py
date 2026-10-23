from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.depositos_a_plazos.control_vencimiento.dependencies import get_control_vencimiento_service
from app.modules.negocios.depositos_a_plazos.control_vencimiento.repositories.sql_control_vencimiento_repository import DetalleVencimientoResultado, SqlControlVencimientoRepository
from app.modules.negocios.depositos_a_plazos.control_vencimiento.schemas import ControlVencimientoRequest, DetalleControlVencimientoRequest
from app.modules.negocios.depositos_a_plazos.control_vencimiento.service import ControlVencimientoService


def auth():
    return AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="Test", id_agencia=2, nombre_agencia="MATRIZ",
        fecha_sistema=date(2026, 10, 23),
    ))


def fila(codigo="ana", agencia=2, saldo="0.10"):
    return dict(codigo=codigo, IDAGENCIA=agencia, agencia=f"AGENCIA {agencia}",
                nombre=codigo, cargo="CAPTADOR", saldo=Decimal(saldo))


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
    return ControlVencimientoRequest(fecha_inicio="2026-10-23", fecha_fin="2026-11-30", **kwargs)


def test_acumula_saldo_exacto_y_conserva_codigo_repetido_en_dos_agencias():
    fuente = Fuente()
    respuesta = ControlVencimientoService(fuente, fuente).obtener(request(), auth())
    assert respuesta.saldo_total == 100.64
    assert len(respuesta.filas) == 3
    assert {fila.clave for fila in respuesta.filas} == {"ana::2", "bea::2", "ana::17"}
    assert fuente.agencias_gerentes == ["AGENCIA 17", "AGENCIA 2"]
    assert respuesta.fecha_sistema == date(2026, 10, 23)


def test_rango_futuro_de_varios_meses_y_agencia_se_delegan_a_la_consulta():
    fuente = Fuente()
    body = ControlVencimientoRequest(fecha_inicio="2026-12-20", fecha_fin="2027-02-15", id_agencia=2)
    ControlVencimientoService(fuente, fuente).obtener(body, auth())
    assert fuente.calls == [dict(fecha_inicio=date(2026, 12, 20), fecha_fin=date(2027, 2, 15), id_agencia=2)]


def test_agencia_inexistente_se_rechaza_antes_de_consultar_depositos():
    fuente = Fuente()
    with pytest.raises(HTTPException) as error:
        ControlVencimientoService(fuente, fuente).obtener(request(id_agencia=99), auth())
    assert error.value.status_code == 404
    assert fuente.calls == []


def test_sin_vencimientos_devuelve_cero_y_lista_vacia():
    fuente = Fuente([])
    resultado = ControlVencimientoService(fuente, fuente).obtener(request(), auth())
    assert resultado.saldo_total == 0
    assert resultado.filas == []
    assert resultado.agencias_gerentes_oficina == []


@pytest.mark.parametrize("inicio,fin", [("2026-11-01", "2026-10-31"), ("2026-10-01", "9999-12-31")])
def test_valida_orden_y_limite_superior_del_rango(inicio, fin):
    with pytest.raises(ValidationError):
        ControlVencimientoRequest(fecha_inicio=inicio, fecha_fin=fin)


def test_endpoint_bearer_contrato_sin_variaciones_y_filtros_obligatorios():
    client = TestClient(app)
    url = "/negocios/depositos-a-plazos/control-vencimiento"
    body = request().model_dump(mode="json")
    assert client.post(url, json=body).status_code == 401
    fuente = Fuente()
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_control_vencimiento_service] = lambda: ControlVencimientoService(fuente, fuente)
    try:
        response = client.post(url, json=body)
        assert response.status_code == 200
        datos = response.json()
        assert datos["saldo_total"] == 100.64
        assert datos["fecha_fin"] == "2026-11-30"
        assert set(datos["filas"][0]) == {
            "Clave", "CodigoUsuario", "NombreCaptador", "Cargo", "IdAgencia", "Agencia", "Saldo",
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
    filas = SqlControlVencimientoRepository(db).obtener_saldos(fecha_inicio=inicio, fecha_fin=fin, id_agencia=2)
    sql, params = db.calls[0]
    assert params == {"fecha_inicio": inicio, "hasta_exclusivo": hasta, "id_agencia": 2}
    assert "D.FECHAVENCIMIENTO >= :fecha_inicio" in sql
    assert "D.FECHAVENCIMIENTO < :hasta_exclusivo" in sql
    assert "D.IDAGENCIA = :id_agencia" in sql
    assert filas[0]["saldo"] == Decimal("123.45")


def test_consulta_consolidada_no_restringe_por_agencia():
    db = SessionFake()
    SqlControlVencimientoRepository(db).obtener_saldos(fecha_inicio=date(2026, 10, 23), fecha_fin=date(2026, 11, 30), id_agencia=0)
    assert "D.IDAGENCIA = :id_agencia" not in db.calls[0][0]


def item_detalle():
    return dict(
        id_deposito=10, numero_cliente=123, nombre_cliente="CLIENTE PRUEBA",
        agencia="MATRIZ", captador="ANA", numero_deposito="DPF-001",
        monto=Decimal("3000.00"), interes_total=Decimal("125.50"), tasa_total=Decimal("7.25"),
        tiene_prestamo=True, fecha_vencimiento=date(2026, 11, 30), estado="Activo",
    )


class FuenteDetalle(Fuente):
    def obtener_detalle(self, **kwargs):
        self.calls.append(kwargs)
        return DetalleVencimientoResultado(120, Decimal("6000"), Decimal("250"), [item_detalle()])


def test_detalle_conserva_agencia_captador_cargos_y_totales_de_todo_el_filtro():
    fuente = FuenteDetalle()
    body = DetalleControlVencimientoRequest(**request(id_agencia=2).model_dump(),
        codigo_usuario=" ana ", cargos=[" CAPTADOR ", "CAPTADOR"], pagina=2, tamano_pagina=50)
    respuesta = ControlVencimientoService(fuente, fuente).obtener_detalle(body)
    assert fuente.calls == [body.model_dump()]
    assert respuesta.codigo_usuario == "ana"
    assert respuesta.cargos == ["CAPTADOR"]
    assert respuesta.total_monto == 6000
    assert respuesta.total_interes == 250
    assert respuesta.total_registros == 120
    assert respuesta.items[0].numero_cliente == "123"
    assert respuesta.items[0].interes_total == 125.50
    assert respuesta.items[0].tasa_total == 7.25
    assert respuesta.items[0].tiene_prestamo is True


def test_detalle_sin_paginacion_devuelve_todos_y_omite_la_pagina():
    fuente = FuenteDetalle()
    body = DetalleControlVencimientoRequest(**request().model_dump(), sin_paginacion=True)
    respuesta = ControlVencimientoService(fuente, fuente).obtener_detalle(body)

    assert fuente.calls == [body.model_dump()]
    assert respuesta.pagina is None
    assert respuesta.tamano_pagina is None
    assert respuesta.total_registros == 120


@pytest.mark.parametrize("campos", [
    {"pagina": 0}, {"tamano_pagina": 0}, {"tamano_pagina": 501},
    {"codigo_usuario": " "}, {"cargos": [" "]},
])
def test_detalle_valida_paginacion_y_filtros(campos):
    with pytest.raises(ValidationError):
        DetalleControlVencimientoRequest(**request().model_dump(), **campos)


def test_endpoint_detalle_requiere_bearer_y_devuelve_campos_solicitados():
    url = "/negocios/depositos-a-plazos/control-vencimiento/detalle"
    client = TestClient(app)
    body = {**request().model_dump(mode="json"), "codigo_usuario": "ana", "cargos": ["CAPTADOR"]}
    assert client.post(url, json=body).status_code == 401
    fuente = FuenteDetalle()
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_control_vencimiento_service] = lambda: ControlVencimientoService(fuente, fuente)
    try:
        respuesta = client.post(url, json=body)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert set(datos["items"][0]) == {
            "id_deposito", "numero_cliente", "nombre_cliente", "agencia", "captador", "numero_deposito",
            "monto", "interes_total", "tasa_total", "tiene_prestamo", "fecha_vencimiento", "estado",
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
        return dict(total_registros=self.total, total_monto=Decimal("6000.00"), total_interes=Decimal("250.00"))

    def all(self):
        return [item_detalle()]


class SessionDetalle:
    def __init__(self, total=120):
        self.total, self.calls = total, []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return ResultadoDetalle(self.total)


def test_consulta_detalle_parametriza_filtros_y_suma_interes_incluyendo_pagados():
    db = SessionDetalle()
    cargo = "CAPTADOR'); SELECT 1; --"
    resultado = SqlControlVencimientoRepository(db).obtener_detalle(
        fecha_inicio=date(2026, 10, 23), fecha_fin=date(2026, 11, 30), id_agencia=2,
        codigo_usuario="ana", cargos=[cargo], pagina=2, tamano_pagina=50,
    )
    assert len(db.calls) == 2
    for sql, params in db.calls:
        assert cargo not in sql
        assert params["cargo_0"] == cargo
        assert params["codigo_usuario"] == "ana"
        assert params["hasta_exclusivo"] == date(2026, 12, 1)
        assert "SUM(IP.CALCULADO)" in sql
        assert "COBRADO" not in sql
        assert "IP.IDITEMPLAZO = 2" in sql
    assert db.calls[1][1]["offset"] == 50
    assert db.calls[1][1]["tamano_pagina"] == 50
    assert resultado.total_monto == Decimal("6000.00")
    assert resultado.items[0]["monto"] == Decimal("3000.00")


def test_detalle_sin_paginacion_consulta_todas_las_filas_sin_offset():
    db = SessionDetalle(total=120)
    resultado = SqlControlVencimientoRepository(db).obtener_detalle(
        fecha_inicio=date(2026, 10, 23), fecha_fin=date(2026, 11, 30), id_agencia=0,
        codigo_usuario=None, cargos=[], pagina=1, tamano_pagina=100, sin_paginacion=True,
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
    resultado = SqlControlVencimientoRepository(db).obtener_detalle(
        fecha_inicio=date(2026, 10, 23), fecha_fin=date(2026, 11, 30), id_agencia=0,
        codigo_usuario=None, cargos=[], pagina=pagina, tamano_pagina=50,
    )
    assert len(db.calls) == 1
    assert resultado.items == []
    assert resultado.total_registros == total
