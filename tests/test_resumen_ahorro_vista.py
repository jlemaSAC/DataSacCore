from datetime import date, datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pymongo.errors import ConnectionFailure

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.dependencies import get_resumen_ahorro_vista_service
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.repositories.mongo_resumen_ahorro_vista_repository import MongoResumenAhorroVistaRepository
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.repositories.sql_resumen_ahorro_vista_repository import (
    CorteAhorroVistaNoDisponible,
    SqlResumenAhorroVistaRepository,
)
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.schemas import InputResumenAhorroVista
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.service import ResumenAhorroVistaService

URL = "/negocios/ahorro-vista/resumen-ahorro-vista"


def auth():
    return AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="Test", id_agencia=1, nombre_agencia="MATRIZ",
        fecha_sistema=date(2026, 8, 31),
    ))


def request(**cambios):
    return InputResumenAhorroVista(**{
        "fecha_inicio": "2026-08-01", "fecha_fin": "2026-08-20", **cambios,
    })


def fila(**cambios):
    return dict(agencia="MATRIZ", asesor="ANA", estado="ACTIVA", producto_ahorro="VISTA",
                saldo=900, numero_cuentas=3, tasa_decimal=1) | cambios


class Sql:
    def __init__(self, filas=None):
        self.filas = filas if filas is not None else [
            fila(), fila(asesor="LUIS", estado="INACTIVA", producto_ahorro="CUENTA BÁSICA",
                         saldo=100, numero_cuentas=1, tasa_decimal=9),
            fila(agencia="CUENCA", saldo=50, numero_cuentas=2, tasa_decimal=0),
        ]
        self.solicitudes = []
        self.solicitudes_diario = []

    def obtener_corte(self, fecha, es_programado=False):
        self.solicitudes.append(fecha)
        return fecha, self.filas

    def obtener_saldos_diarios(self, fecha_inicio, fecha_fin, agencias, es_programado=False):
        self.solicitudes_diario.append((fecha_inicio, fecha_fin, agencias))
        return []


class Mongo:
    def __init__(self, filas=None):
        self.filas = filas
        self.solicitudes = []

    def obtener_corte(self, fecha, es_programado=False):
        self.solicitudes.append(fecha)
        return self.filas


def test_mismo_universo_y_tasa_ponderada_en_todas_las_dimensiones():
    sql, mongo = Sql(), Mongo([fila(saldo=800)])
    result = ResumenAhorroVistaService(sql, mongo).obtener_resumen(request(), auth())
    assert result.actual.saldo == 1050
    assert result.actual.numero_cuentas == 6
    assert result.actual.tasa_promedio == 2  # (3*1 + 1*9 + 2*0) / 6
    for grupos in (result.por_agencia, result.por_asesor, result.por_estado, result.por_producto_ahorro):
        assert sum(f.saldo for f in grupos) == 1050
        assert sum(f.numero_cuentas for f in grupos) == 6
    assert sql.solicitudes == [date(2026, 8, 20)]
    assert mongo.solicitudes == [date(2026, 7, 31), date(2025, 12, 31)]
    assert result.mes_anterior.saldo == 800


def test_filtra_agencias_normalizadas_y_no_suma_cortes_ni_promedia_grupos():
    service = ResumenAhorroVistaService(Sql(), Mongo([fila()]))
    result = service.obtener_resumen(request(agencias=[" matriz ", "MATRIZ"]), auth())
    assert result.agencias == ["MATRIZ"]
    assert result.actual.saldo == 1000
    assert result.actual.numero_cuentas == 4
    assert result.actual.tasa_promedio == 3
    assert result.mes_anterior.numero_cuentas == 3
    assert result.por_agencia[0].tasa_promedio == 3
    # Es un saldo al corte final, no un flujo acumulado dentro del rango.
    other = service.obtener_resumen(request(fecha_inicio="2026-08-15", agencias=["MATRIZ"]), auth())
    assert other.actual == result.actual


def test_historico_faltante_o_mongo_caido_se_reconstruye_en_sql():
    for mongo in (Mongo(), MongoCaido()):
        sql = Sql()
        result = ResumenAhorroVistaService(sql, mongo).obtener_resumen(request(), auth())
        assert result.mes_anterior.saldo == 1050
        assert sql.solicitudes == [date(2026, 8, 20), date(2026, 7, 31), date(2025, 12, 31)]


class MongoCaido:
    def obtener_corte(self, fecha, es_programado=False):
        raise ConnectionFailure("unavailable")


def test_sin_cuentas_tiene_cero_y_tasa_nula_pero_sin_cierre_no_inventa_cero():
    result = ResumenAhorroVistaService(Sql([]), Mongo()).obtener_resumen(request(), auth())
    assert result.actual.saldo == 0
    assert result.actual.numero_cuentas == 0
    assert result.actual.tasa_promedio is None
    assert result.por_agencia == []

    class SqlSinHistorico(Sql):
        def obtener_corte(self, fecha, es_programado=False):
            if fecha == date(2026, 8, 20):
                return super().obtener_corte(fecha, es_programado=es_programado)
            raise CorteAhorroVistaNoDisponible("Falta el cierre histórico")

    result = ResumenAhorroVistaService(SqlSinHistorico(), Mongo()).obtener_resumen(request(), auth())
    assert result.mes_anterior is None
    assert result.anio_anterior is None


def test_corte_actual_no_disponible_y_fecha_futura():
    class SinCorte(Sql):
        def obtener_corte(self, fecha, es_programado=False):
            raise CorteAhorroVistaNoDisponible("Falta cierre")

    with pytest.raises(HTTPException) as error:
        ResumenAhorroVistaService(SinCorte(), Mongo()).obtener_resumen(request(), auth())
    assert error.value.status_code == 409
    sql = Sql()
    with pytest.raises(HTTPException) as error:
        ResumenAhorroVistaService(sql, Mongo()).obtener_resumen(
            request(fecha_inicio="2026-09-01", fecha_fin="2026-09-02"), auth())
    assert error.value.status_code == 400
    assert sql.solicitudes == []


def test_enero_consulta_una_sola_vez_el_cierre_compartido():
    sql, mongo = Sql(), Mongo([fila()])
    result = ResumenAhorroVistaService(sql, mongo).obtener_resumen(
        request(fecha_inicio="2026-01-01", fecha_fin="2026-01-20"), auth())
    assert mongo.solicitudes == [date(2025, 12, 31)]
    assert result.mes_anterior == result.anio_anterior


def test_saldo_diario_cubre_rango_inclusivo_y_reutiliza_saldo_final():
    class Fuente(Sql):
        def obtener_saldos_diarios(self, inicio, fin, agencias, es_programado=False):
            self.solicitudes_diario.append((inicio, fin, agencias))
            return [
                {"fecha": date(2026, 8, 17), "saldo": 700.25},
                {"fecha": date(2026, 8, 19), "saldo": 0},
            ]

    sql = Fuente()
    resultado = ResumenAhorroVistaService(sql, Mongo()).obtener_resumen(
        request(fecha_inicio="2026-08-17", agencias=[" matriz "]), auth(),
    )
    assert [d.fecha for d in resultado.saldo_diario] == [
        date(2026, 8, dia) for dia in range(17, 21)
    ]
    assert [d.saldo for d in resultado.saldo_diario] == [700.25, None, 0, 1000]
    assert resultado.saldo_diario[-1].saldo == resultado.actual.saldo
    assert sql.solicitudes_diario == [(date(2026, 8, 17), date(2026, 8, 19), ["MATRIZ"])]
    assert sql.solicitudes.count(date(2026, 8, 20)) == 1


def test_rango_de_un_dia_solo_devuelve_el_corte_seleccionado():
    sql = Sql()
    resultado = ResumenAhorroVistaService(sql, Mongo()).obtener_resumen(
        request(fecha_inicio="2026-08-20"), auth(),
    )
    assert len(resultado.saldo_diario) == 1
    assert resultado.saldo_diario[0].saldo == resultado.actual.saldo


def test_diario_no_presenta_un_corte_anterior_como_saldo_del_dia_final():
    class Fuente(Sql):
        def obtener_corte(self, fecha, es_programado=False):
            return date(2026, 8, 19), self.filas

    resultado = ResumenAhorroVistaService(Fuente(), Mongo()).obtener_resumen(
        request(fecha_inicio="2026-08-20"), auth(),
    )
    assert resultado.actual.fecha_corte == date(2026, 8, 19)
    assert resultado.saldo_diario[0].saldo is None


@pytest.mark.parametrize("es_programado", [False, True])
def test_sql_diario_consulta_cierres_en_bloque_y_parametriza_agencias(es_programado):
    cierres = [
        {"fecha": date(2026, 11, 1), "cierre": datetime(2026, 11, 2, 3)},
        {"fecha": date(2026, 11, 3), "cierre": datetime(2026, 11, 4, 3)},
    ]
    dias = [{"fecha": c["fecha"], "saldo": 700} for c in cierres]

    class DB:
        def __init__(self):
            self.consultas = []

        def execute(self, query, parametros):
            self.consultas.append((str(query), parametros))
            return self

        def mappings(self):
            return self

        def all(self):
            return cierres if len(self.consultas) == 1 else dias

    db = DB()
    resultado = SqlResumenAhorroVistaRepository(db).obtener_saldos_diarios(
        date(2026, 11, 1), date(2026, 11, 3), ["MATRIZ"], es_programado=es_programado,
    )
    assert resultado == dias
    assert len(db.consultas) == 2
    query, parametros = db.consultas[1]
    assert query.count("TC.ESPROGRAMADO = :es_programado") == 2
    assert parametros["es_programado"] is es_programado
    assert query.count("FOR SYSTEM_TIME AS OF") == 4
    assert " UNION ALL " in query
    assert "MATRIZ" not in query
    assert parametros["agencias"] == ["MATRIZ"]
    assert parametros["cierre_0"] == cierres[0]["cierre"]
    assert parametros["cierre_1"] == cierres[1]["cierre"]
    assert "CUENTA_PROGRAMADO" not in query


def test_sql_diario_no_consulta_saldos_si_no_existen_cierres_o_el_rango_es_vacio():
    class DB:
        def __init__(self):
            self.consultas = 0

        def execute(self, query, parametros):
            self.consultas += 1
            return self

        def mappings(self):
            return self

        def all(self):
            return []

    db = DB()
    repo = SqlResumenAhorroVistaRepository(db)
    assert repo.obtener_saldos_diarios(date(2026, 11, 2), date(2026, 11, 1), []) == []
    assert db.consultas == 0
    assert repo.obtener_saldos_diarios(date(2026, 11, 1), date(2026, 11, 3), []) == []
    assert db.consultas == 1


@pytest.mark.parametrize("incompletas", [0, 1])
def test_mongo_no_equivale_documentos_a_cuentas(incompletas):
    class Collection:
        def aggregate(self, pipeline):
            assert pipeline[0] == {"$match": {"fecha_corte": "20260731", "es_programado": False}}
            return [{"_id": {k: v for k, v in fila().items() if k not in ("saldo", "numero_cuentas")},
                     "saldo": 900, "numero_cuentas": 3, "incompletas": incompletas}]

    result = MongoResumenAhorroVistaRepository({"ReporteAnaliticoAhorrosVistaMensual": Collection()}).obtener_corte(date(2026, 7, 31))
    assert result is None if incompletas else result[0]["numero_cuentas"] == 3


@pytest.mark.parametrize("es_programado, saldo, cuentas", [(False, 900, 3), (True, 8000, 20)])
def test_mongo_filtra_programados_y_excluye_documentos_sin_clasificacion(es_programado, saldo, cuentas):
    documentos = [
        fila(es_programado=False, fecha_corte="20260731"),
        # El nombre no determina el universo: se usa el booleano del analítico.
        fila(es_programado=True, fecha_corte="20260731", saldo=8000, numero_cuentas=20),
        fila(fecha_corte="20260731", saldo=3000, numero_cuentas=10),
        fila(es_programado=False, fecha_corte="20260630", saldo=5000, numero_cuentas=30),
    ]

    class Collection:
        def aggregate(self, pipeline):
            filtro = pipeline[0]["$match"]
            return [
                {
                    "_id": {k: d[k] for k in (
                        "agencia", "asesor", "estado", "producto_ahorro", "tasa_decimal"
                    )},
                    "saldo": d["saldo"], "numero_cuentas": d["numero_cuentas"], "incompletas": 0,
                }
                for d in documentos if all(d.get(k) == v for k, v in filtro.items())
            ]

    filas = MongoResumenAhorroVistaRepository({
        "ReporteAnaliticoAhorrosVistaMensual": Collection(),
    }).obtener_corte(date(2026, 7, 31), es_programado=es_programado)
    assert len(filas) == 1
    assert sum(f["numero_cuentas"] for f in filas) == cuentas
    assert sum(f["saldo"] for f in filas) == saldo


@pytest.mark.parametrize("historico", [False, True])
@pytest.mark.parametrize("es_programado", [False, True])
def test_sql_filtra_programados_en_corte_actual_e_historico(historico, es_programado):
    fecha = date(2026, 10, 31) if historico else date(2026, 11, 6)
    cierre = datetime(2026, 11, 1, 1, 30) if historico else None

    class DB:
        def __init__(self):
            self.consultas = []

        def execute(self, query, parametros):
            self.consultas.append((str(query), parametros))
            return self

        def mappings(self):
            return self

        def first(self):
            return {"fecha_corte": fecha, "fecha_sistema": date(2026, 11, 6), "cierre": cierre}

        def all(self):
            return [fila()]

    db = DB()
    corte, filas = SqlResumenAhorroVistaRepository(db).obtener_corte(fecha, es_programado=es_programado)
    assert corte == fecha
    assert filas == [fila()]
    query, parametros = db.consultas[1]
    assert "TipoCuenta.ESPROGRAMADO = :es_programado" in query
    assert "CUENTA_PROGRAMADO" not in query
    assert "COALESCE(T.tasa, 0)" in query
    assert ("FOR SYSTEM_TIME AS OF :cierre" in query) is historico
    assert parametros == {"cierre": cierre, "es_programado": es_programado}


def test_sql_no_sustituye_un_cierre_faltante_con_saldos_actuales():
    class DB:
        def __init__(self):
            self.consultas = 0

        def execute(self, query, parametros):
            self.consultas += 1
            return self

        def mappings(self):
            return self

        def first(self):
            return {"fecha_corte": date(2026, 10, 31), "fecha_sistema": date(2026, 11, 6), "cierre": None}

    db = DB()
    with pytest.raises(CorteAhorroVistaNoDisponible):
        SqlResumenAhorroVistaRepository(db).obtener_corte(date(2026, 10, 31))
    assert db.consultas == 1


def test_endpoint_contrato_validaciones_y_bearer():
    assert TestClient(app).post(URL, json=request().model_dump(mode="json")).status_code == 401
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_resumen_ahorro_vista_service] = lambda: ResumenAhorroVistaService(Sql(), Mongo())
    try:
        client = TestClient(app)
        response = client.post(URL, json=request().model_dump(mode="json"))
        assert response.status_code == 200
        assert response.json()["actual"]["numero_cuentas"] == 6
        assert response.json()["por_producto_ahorro"]
        assert len(response.json()["saldo_diario"]) == 20
        assert response.json()["saldo_diario"][-1] == {"fecha": "2026-08-20", "saldo": 1050}
        for body in (
            {"fecha_inicio": "2026-08-01", "fecha_fin": "2026-09-02"},
            {"fecha_inicio": "2026-08-20", "fecha_fin": "2026-08-01"},
            {"fecha_inicio": "2026-08-01", "fecha_fin": "2026-08-20", "agencias": [""]},
            {"fecha_inicio": "2026-08-01", "fecha_fin": "2026-08-20", "es_programado": "invalido"},
        ):
            assert client.post(URL, json=body).status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("es_programado", [False, True])
@pytest.mark.parametrize("reconstruir", [False, True])
def test_programado_se_propaga_a_actual_comparativos_fallback_y_diario(es_programado, reconstruir):
    class FuenteSql(Sql):
        def obtener_corte(self, fecha, es_programado=False):
            self.solicitudes.append((fecha, es_programado))
            return fecha, [fila(saldo=500 if es_programado else 100)]

        def obtener_saldos_diarios(self, inicio, fin, agencias, es_programado=False):
            self.solicitudes_diario.append((inicio, fin, agencias, es_programado))
            return [{"fecha": inicio, "saldo": 300 if es_programado else 50}]

    class FuenteMongo(Mongo):
        def obtener_corte(self, fecha, es_programado=False):
            self.solicitudes.append((fecha, es_programado))
            return None if reconstruir else [fila(saldo=400 if es_programado else 80)]

    sql, mongo = FuenteSql(), FuenteMongo()
    resultado = ResumenAhorroVistaService(sql, mongo).obtener_resumen(
        request(es_programado=es_programado), auth(),
    )
    assert resultado.actual.saldo == (500 if es_programado else 100)
    assert resultado.mes_anterior.saldo == (
        (500 if es_programado else 100) if reconstruir else (400 if es_programado else 80)
    )
    assert all(programado is es_programado for _, programado in sql.solicitudes + mongo.solicitudes)
    assert len(sql.solicitudes) == (3 if reconstruir else 1)
    assert sql.solicitudes_diario[0][-1] is es_programado
    assert resultado.saldo_diario[0].saldo == (300 if es_programado else 50)
    assert resultado.saldo_diario[-1].saldo == resultado.actual.saldo


@pytest.mark.parametrize("es_programado", [False, True])
def test_endpoint_acepta_filtro_programado_y_conserva_false_por_defecto(es_programado):
    recibidos = []

    class Service:
        def obtener_resumen(self, body, contexto):
            recibidos.append(body.es_programado)
            return ResumenAhorroVistaService(Sql(), Mongo()).obtener_resumen(body, contexto)

    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_resumen_ahorro_vista_service] = Service
    try:
        client = TestClient(app)
        body = {"fecha_inicio": "2026-08-01", "fecha_fin": "2026-08-20"}
        assert client.post(URL, json=body).status_code == 200
        assert client.post(URL, json={**body, "es_programado": es_programado}).status_code == 200
        assert recibidos == [False, es_programado]
    finally:
        app.dependency_overrides.clear()
