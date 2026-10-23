from datetime import date, datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.depositos_a_plazos.evaluacion_captadores.dependencies import get_evaluacion_captadores_service
from app.modules.negocios.depositos_a_plazos.evaluacion_captadores.repositories.sql_evaluacion_captadores_repository import CorteCaptadores, SqlEvaluacionCaptadoresRepository
from app.modules.negocios.depositos_a_plazos.evaluacion_captadores.schemas import EvaluacionCaptadoresRequest
from app.modules.negocios.depositos_a_plazos.evaluacion_captadores.service import EvaluacionCaptadoresService


def auth():
    return AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="Test", id_agencia=2, nombre_agencia="MATRIZ",
        fecha_sistema=date(2026, 10, 21),
    ))


def fila(codigo="ana", agencia=2, *, saldo=100, operaciones=2, suma=16, ingresos=1, suma_ingresos=10):
    return dict(codigo=codigo, IDAGENCIA=agencia, agencia=f"AGENCIA {agencia}", nombre=codigo,
                cargo="CAPTADOR", saldo=saldo, operaciones=operaciones, suma_tasas=suma,
                operaciones_renovacion=ingresos, suma_tasas_renovacion=suma_ingresos)


class Fuente:
    def __init__(self, actual=None, cierre=None):
        self.actual = actual if actual is not None else [fila(), fila("nuevo", ingresos=0, suma_ingresos=0)]
        self.cierre = cierre if cierre is not None else [fila(saldo=80, suma=12), fila("saliente", saldo=50)]
        self.calls = []
        self.sin_cierre = False

    def obtener_corte(self, **kwargs):
        self.calls.append(kwargs)
        if self.sin_cierre:
            return None
        return CorteCaptadores(kwargs["fecha"], self.actual if kwargs["fecha"].month == 10 else self.cierre)

    def obtener_nombre_agencia(self, agencia):
        return "MATRIZ" if agencia == 2 else None

    def obtener_gerentes_oficina(self, agencias):
        return [{"Agencia": a, "GerenteOficina": "Responsable"} for a in agencias]


def request(**kwargs):
    return EvaluacionCaptadoresRequest(fecha_inicio="2026-10-01", fecha_fin="2026-10-21", **kwargs)


def test_compara_usuarios_nuevos_salientes_y_tasas_sin_referencia():
    fuente = Fuente()
    respuesta = EvaluacionCaptadoresService(fuente, fuente).obtener(request(), auth())
    filas = {f.codigo_usuario: f for f in respuesta.comparacion}
    assert respuesta.fecha_corte_cierre_mes_anterior == date(2026, 9, 30)
    assert filas["ana"].valores_actual.tasa_promedio == 8
    assert filas["ana"].valores_actual.tasa_promedio_renovacion == 10
    assert filas["ana"].diferencias_cierre_mes_anterior.saldo_deposito == 20
    assert filas["ana"].diferencias_cierre_mes_anterior.tasa_promedio == 2
    assert filas["nuevo"].valores_actual.tasa_promedio_renovacion is None
    assert filas["nuevo"].diferencias_cierre_mes_anterior.tasa_promedio is None
    assert filas["saliente"].valores_actual is None
    assert filas["saliente"].diferencias_cierre_mes_anterior.saldo_deposito == -50
    assert respuesta.faltantes_en_cierre_mes_anterior == ["nuevo::2"]
    assert respuesta.faltantes_en_actual == ["saliente::2"]
    assert fuente.calls[0]["fecha_ingreso_desde"] == date(2026, 10, 1)
    assert fuente.calls[1]["fecha_ingreso_desde"] == date(2026, 9, 1)


def test_codigo_usuario_repetido_en_dos_agencias_no_se_sobrescribe():
    fuente = Fuente(actual=[fila(), fila(agencia=17)], cierre=[])
    respuesta = EvaluacionCaptadoresService(fuente, fuente).obtener(request(), auth())
    assert len(respuesta.comparacion) == 2
    assert {f.clave for f in respuesta.comparacion} == {"ana::2", "ana::17"}
    assert sum(f.valores_actual.saldo_deposito for f in respuesta.comparacion) == 200


def test_rango_custom_delimita_ingresos_y_agencia_en_las_dos_consultas():
    fuente = Fuente()
    body = EvaluacionCaptadoresRequest(fecha_inicio="2026-10-10", fecha_fin="2026-10-20", id_agencia=2)
    EvaluacionCaptadoresService(fuente, fuente).obtener(body, auth())
    assert fuente.calls[0]["fecha_ingreso_desde"] == date(2026, 10, 10)
    assert all(c["id_agencia"] == 2 for c in fuente.calls)


@pytest.mark.parametrize("inicio,fin", [("2026-10-22", "2026-10-21"), ("2026-09-30", "2026-10-21")])
def test_valida_fechas_ordenadas_del_mismo_mes(inicio, fin):
    with pytest.raises(ValidationError):
        EvaluacionCaptadoresRequest(fecha_inicio=inicio, fecha_fin=fin)


def test_fecha_futura_y_agencia_desconocida_no_consultan_depositos():
    fuente = Fuente()
    service = EvaluacionCaptadoresService(fuente, fuente)
    with pytest.raises(HTTPException) as error:
        service.obtener(EvaluacionCaptadoresRequest(fecha_inicio="2026-10-01", fecha_fin="2026-10-22"), auth())
    assert error.value.status_code == 400
    with pytest.raises(HTTPException) as error:
        service.obtener(request(id_agencia=99), auth())
    assert error.value.status_code == 404
    assert fuente.calls == []


def test_cierre_faltante_se_reporta_como_no_disponible():
    fuente = Fuente()
    fuente.sin_cierre = True
    with pytest.raises(HTTPException) as error:
        EvaluacionCaptadoresService(fuente, fuente).obtener(request(), auth())
    assert error.value.status_code == 404


def test_corte_disponible_sin_depositos_devuelve_lista_vacia():
    fuente = Fuente(actual=[], cierre=[])
    respuesta = EvaluacionCaptadoresService(fuente, fuente).obtener(request(), auth())
    assert respuesta.comparacion == []


def test_endpoint_bearer_y_contrato_comparativo():
    client = TestClient(app)
    url = "/negocios/depositos-a-plazos/evaluacion-captadores"
    assert client.post(url, json=request().model_dump(mode="json")).status_code == 401
    fuente = Fuente()
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_evaluacion_captadores_service] = lambda: EvaluacionCaptadoresService(fuente, fuente)
    try:
        response = client.post(url, json=request().model_dump(mode="json"))
        assert response.status_code == 200
        datos = response.json()
        assert datos["fecha_corte_actual"] == "2026-10-21"
        assert datos["comparacion"][0]["ValoresActual"]["SaldoDeposito"] == 100
        assert datos["comparacion"][0]["ValoresActual"]["SumaTasas"] == 16
        assert datos["agencias_gerentes_oficina"][0]["GerenteOficina"] == "Responsable"
        assert client.post(url, json={**request().model_dump(mode="json"), "filtrar_diferidos": True}).status_code == 422
    finally:
        app.dependency_overrides.clear()


class Resultado:
    def __init__(self, first=None, all=None):
        self.row, self.rows = first, all or []

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
        return Resultado(first=self.corte) if len(self.calls) == 1 else Resultado(all=[fila()])


@pytest.mark.parametrize("fecha,en_linea", [(date(2026, 10, 21), True), (date(2026, 9, 30), False)])
def test_repositorio_usa_fuente_temporal_y_limites_inclusivos(fecha, en_linea):
    db = SessionFake({"fecha": fecha, "cerrado": not en_linea, "cierre": datetime(2026, 10, 1, 2, 59)})
    resultado = SqlEvaluacionCaptadoresRepository(db).obtener_corte(
        fecha=fecha, fecha_sistema=date(2026, 10, 21), fecha_ingreso_desde=fecha.replace(day=1), id_agencia=2,
    )
    sql, params = db.calls[1]
    assert ("FOR SYSTEM_TIME AS OF :cierre" in sql) is not en_linea
    assert "IN ('A', 'E', 'V')" in sql
    assert "< :ingreso_hasta" in sql
    assert params["id_agencia"] == 2
    assert params["ingreso_hasta"].day == (22 if en_linea else 1)
    assert resultado.fecha == fecha


def test_repositorio_no_sustituye_cierre_historico_faltante_por_datos_vivos():
    db = SessionFake({"fecha": date(2026, 9, 30), "cerrado": True, "cierre": None})
    assert SqlEvaluacionCaptadoresRepository(db).obtener_corte(
        fecha=date(2026, 9, 30), fecha_sistema=date(2026, 10, 21),
        fecha_ingreso_desde=date(2026, 9, 1), id_agencia=0,
    ) is None
    assert len(db.calls) == 1


def test_token_con_fecha_antigua_no_usa_datos_en_linea_para_un_dia_ya_cerrado():
    db = SessionFake({"fecha": date(2026, 10, 20), "cerrado": True, "cierre": datetime(2026, 10, 21, 2)})
    SqlEvaluacionCaptadoresRepository(db).obtener_corte(
        fecha=date(2026, 10, 20), fecha_sistema=date(2026, 10, 20),
        fecha_ingreso_desde=date(2026, 10, 1), id_agencia=0,
    )
    assert "FOR SYSTEM_TIME AS OF :cierre" in db.calls[1][0]
