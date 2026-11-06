from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.ahorro_vista.evaluacion_cuentas_ahorro_vista.dependencies import (
    get_evaluacion_cuentas_ahorro_vista_service,
)
from app.modules.negocios.ahorro_vista.evaluacion_cuentas_ahorro_vista.repositories.sql_evaluacion_cuentas_ahorro_vista_repository import (
    CorteEvaluacionAhorroVista,
    SqlEvaluacionCuentasAhorroVistaRepository,
)
from app.modules.negocios.ahorro_vista.evaluacion_cuentas_ahorro_vista.schemas import (
    EvaluacionCuentasAhorroVistaRequest,
)
from app.modules.negocios.ahorro_vista.evaluacion_cuentas_ahorro_vista.service import (
    EvaluacionCuentasAhorroVistaService,
)


URL = "/negocios/ahorro-vista/evaluacion-cuentas-ahorro-vista"


def auth():
    return AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="Test", id_agencia=2, nombre_agencia="MATRIZ",
        fecha_sistema=datetime(2026, 11, 6),
    ))


def request(**cambios):
    return EvaluacionCuentasAhorroVistaRequest(**{
        "fecha_inicio": "2026-11-01", "fecha_fin": "2026-11-06", **cambios,
    })


def fila(**cambios):
    return dict(
        codigo_usuario="ana", id_agencia=2, codigo_producto="002", producto_ahorro="Ahorro Vista",
        agencia="MATRIZ", nombre="Ana", saldo=Decimal("100.25"), cuentas=3, suma_tasas=6,
    ) | cambios


class Fuente:
    def __init__(self, actual=None, cierre=None):
        self.actual = actual if actual is not None else [fila(), fila(codigo_producto="005", producto_ahorro="Cuenta Básica", cuentas=1, suma_tasas=8)]
        self.cierre = cierre if cierre is not None else [fila(saldo=80, cuentas=2, suma_tasas=2), fila(codigo_usuario="saliente")]
        self.calls = []
        self.fechas_faltantes = set()
        self.gerentes_calls = []

    def obtener_corte(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["fecha"] in self.fechas_faltantes:
            return None
        filas = self.actual if kwargs["fecha"] == date(2026, 11, 6) else self.cierre
        return CorteEvaluacionAhorroVista(kwargs["fecha"], filas)

    def obtener_nombre_agencia(self, id_agencia):
        return "MATRIZ" if id_agencia == 2 else None

    def obtener_gerentes_oficina(self, agencias):
        self.gerentes_calls.append(agencias)
        return [{"Agencia": a, "GerenteOficina": "Responsable"} for a in agencias]


def test_compara_cortes_y_conserva_productos_nuevos_y_salientes():
    fuente = Fuente()
    resultado = EvaluacionCuentasAhorroVistaService(fuente, fuente).obtener(request(), auth())
    filas = {f.clave: f for f in resultado.comparacion}
    vista, basica, saliente = (filas[c] for c in ("ana::2::002", "ana::2::005", "saliente::2::002"))
    assert resultado.fecha_corte_cierre_mes_anterior == date(2026, 10, 31)
    assert vista.valores_actual.saldo == 100.25
    assert vista.valores_actual.cuentas == 3
    assert vista.valores_actual.tasa_promedio == 2
    assert vista.diferencias_cierre_mes_anterior.model_dump() == {
        "saldo": 20.25, "cuentas": 1, "tasa_promedio": 1,
    }
    assert basica.valores_cierre_mes_anterior is None
    assert basica.diferencias_cierre_mes_anterior.tasa_promedio is None
    assert saliente.valores_actual is None
    assert saliente.diferencias_cierre_mes_anterior.saldo == -100.25
    assert saliente.diferencias_cierre_mes_anterior.cuentas == -3
    assert resultado.faltantes_en_cierre_mes_anterior == ["ana::2::005"]
    assert resultado.faltantes_en_actual == ["saliente::2::002"]
    assert fuente.gerentes_calls == [["MATRIZ"]]


def test_filtro_producto_y_reagrupacion_no_promedian_promedios():
    fuente = Fuente()
    resultado = EvaluacionCuentasAhorroVistaService(fuente, fuente).obtener(request(), auth())
    actuales = [f for f in resultado.comparacion if f.valores_actual is not None]
    assert sum(f.valores_actual.suma_tasas for f in actuales) / sum(f.valores_actual.cuentas for f in actuales) == 3.5
    vista = [f for f in actuales if f.codigo_producto == "002"]
    assert sum(f.valores_actual.suma_tasas for f in vista) / sum(f.valores_actual.cuentas for f in vista) == 2
    assert {f.producto_ahorro for f in resultado.comparacion} == {"Ahorro Vista", "Cuenta Básica"}


def test_mismo_asesor_en_distintas_agencias_y_productos_no_se_sobrescribe():
    fuente = Fuente(actual=[fila(), fila(id_agencia=17, agencia="CUENCA"), fila(codigo_producto="005")], cierre=[])
    resultado = EvaluacionCuentasAhorroVistaService(fuente, fuente).obtener(request(id_agencia=2), auth())
    assert {f.clave for f in resultado.comparacion} == {"ana::2::002", "ana::17::002", "ana::2::005"}
    assert sum(f.valores_actual.cuentas for f in resultado.comparacion) == 9
    assert all(c["id_agencia"] == 2 for c in fuente.calls)
    assert all(c["fecha_sistema"] == date(2026, 11, 6) for c in fuente.calls)


def test_rango_no_filtra_aperturas_y_enero_compara_diciembre():
    fuente = Fuente()
    service = EvaluacionCuentasAhorroVistaService(fuente, fuente)
    primero = service.obtener(request(), auth())
    segundo = service.obtener(request(fecha_inicio="2026-11-05"), auth())
    assert primero.comparacion == segundo.comparacion
    assert fuente.calls[:2] == fuente.calls[2:]
    service.obtener(request(fecha_inicio="2026-01-05", fecha_fin="2026-01-20"), auth())
    assert fuente.calls[-1]["fecha"] == date(2025, 12, 31)


@pytest.mark.parametrize("cambios", [
    {"fecha_inicio": "2026-11-07"}, {"fecha_inicio": "2026-10-31"},
    {"id_agencia": -1}, {"cargos": ["CAPTADOR"]}, {"es_programado": True},
])
def test_request_rechaza_rangos_y_parametros_invalidos(cambios):
    with pytest.raises(ValidationError):
        request(**cambios)


@pytest.mark.parametrize("cambios,codigo", [({"fecha_fin": "2026-11-07"}, 400), ({"id_agencia": 99}, 404)])
def test_fecha_futura_y_agencia_desconocida_no_consultan_cuentas(cambios, codigo):
    fuente = Fuente()
    with pytest.raises(HTTPException) as error:
        EvaluacionCuentasAhorroVistaService(fuente, fuente).obtener(request(**cambios), auth())
    assert error.value.status_code == codigo
    assert fuente.calls == []


@pytest.mark.parametrize("fecha", [date(2026, 11, 6), date(2026, 10, 31)])
def test_cierre_faltante_no_se_confunde_con_cero(fecha):
    fuente = Fuente()
    fuente.fechas_faltantes.add(fecha)
    with pytest.raises(HTTPException) as error:
        EvaluacionCuentasAhorroVistaService(fuente, fuente).obtener(request(), auth())
    assert error.value.status_code == 404
    assert str(fecha) in error.value.detail


def test_cortes_vacios_y_cuentas_sin_tasa_configurada():
    fuente = Fuente(actual=[], cierre=[])
    service = EvaluacionCuentasAhorroVistaService(fuente, fuente)
    assert service.obtener(request(), auth()).comparacion == []
    fuente.actual = [fila(saldo=0, cuentas=1, suma_tasas=0)]
    valores = service.obtener(request(), auth()).comparacion[0].valores_actual
    assert valores.saldo == 0
    assert valores.tasa_promedio == 0


def test_endpoint_bearer_contrato_y_validacion():
    client = TestClient(app)
    body = request().model_dump(mode="json")
    assert client.post(URL, json=body).status_code == 401
    fuente = Fuente()
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_evaluacion_cuentas_ahorro_vista_service] = lambda: EvaluacionCuentasAhorroVistaService(fuente, fuente)
    try:
        respuesta = client.post(URL, json=body)
        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["fecha_corte_actual"] == "2026-11-06"
        assert datos["comparacion"][0]["ValoresActual"] == {
            "Saldo": 100.25, "Cuentas": 3, "TasaPromedio": 2, "SumaTasas": 6,
        }
        assert datos["comparacion"][0]["CodigoProducto"] == "002"
        assert datos["agencias_gerentes_oficina"][0]["GerenteOficina"] == "Responsable"
        assert client.post(URL, json=body | {"cargos": []}).status_code == 422
        assert client.post(URL, json=body | {"fecha_fin": "2026-11-07"}).status_code == 400
    finally:
        app.dependency_overrides.clear()


class SessionFake:
    def __init__(self, corte):
        self.corte, self.calls = corte, []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return self

    def mappings(self):
        return self

    def first(self):
        return self.corte

    def all(self):
        return [fila()]


@pytest.mark.parametrize("en_linea", [True, False])
@pytest.mark.parametrize("id_agencia", [0, 2])
def test_sql_corte_temporal_mismo_universo_y_filtro_temprano(en_linea, id_agencia):
    fecha = date(2026, 11, 6) if en_linea else date(2026, 10, 31)
    cierre = datetime(2026, 11, 1, 3)
    db = SessionFake({"fecha": datetime.combine(fecha, datetime.min.time()), "cerrado": not en_linea, "cierre": cierre})
    resultado = SqlEvaluacionCuentasAhorroVistaRepository(db).obtener_corte(
        fecha=fecha, fecha_sistema=date(2026, 11, 6), id_agencia=id_agencia,
    )
    sql, params = db.calls[1]
    assert resultado.fecha == fecha
    assert sql.count("FOR SYSTEM_TIME AS OF :cierre") == (0 if en_linea else 4)
    assert "TC.ESPROGRAMADO = 0" in sql
    assert "IN (N'A', N'I', N'B')" in sql
    assert "CU.CODIGOTIPOCUENTA <> N'001'" in sql
    assert ("AND CU.IDAGENCIA = :id_agencia" in sql) == bool(id_agencia)
    assert params == {"cierre": cierre, "id_agencia": id_agencia}
    assert db.calls[0][1]["hasta_exclusivo"] == (date(2026, 11, 7) if en_linea else date(2026, 11, 1))


@pytest.mark.parametrize("corte", [None, {"fecha": date(2026, 10, 31), "cerrado": True, "cierre": None}])
def test_sql_sin_cierre_no_consulta_saldos_vivos(corte):
    db = SessionFake(corte)
    assert SqlEvaluacionCuentasAhorroVistaRepository(db).obtener_corte(
        fecha=date(2026, 10, 31), fecha_sistema=date(2026, 11, 6), id_agencia=0,
    ) is None
    assert len(db.calls) == 1


def test_token_antiguo_y_fecha_cerrada_usan_historia():
    db = SessionFake({"fecha": date(2026, 11, 5), "cerrado": True, "cierre": datetime(2026, 11, 6, 3)})
    SqlEvaluacionCuentasAhorroVistaRepository(db).obtener_corte(
        fecha=date(2026, 11, 5), fecha_sistema=date(2026, 11, 5), id_agencia=0,
    )
    assert "FOR SYSTEM_TIME AS OF :cierre" in db.calls[1][0]
