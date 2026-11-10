from datetime import date, datetime
from decimal import Decimal
import sqlite3

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.dialects import sqlite
from sqlalchemy.exc import DBAPIError

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.ahorro_vista.depositos_y_retiros_diarios.dependencies import (
    get_depositos_y_retiros_diarios_service,
)
from app.modules.negocios.ahorro_vista.depositos_y_retiros_diarios.repositories.sql_depositos_y_retiros_diarios_repository import (
    CorteDepositosYRetiros,
    SqlDepositosYRetirosDiariosRepository,
)
from app.modules.negocios.ahorro_vista.depositos_y_retiros_diarios.schemas import (
    DepositosYRetirosDiariosRequest,
)
from app.modules.negocios.ahorro_vista.depositos_y_retiros_diarios.service import (
    DepositosYRetirosDiariosService,
)
from app.modules.negocios.ahorro_vista.depositos_y_retiros_diarios.repositories import (
    sql_depositos_y_retiros_diarios_repository as diario_sql,
)


URL = "/negocios/ahorro-vista/depositos-y-retiros-diarios"


def auth():
    return AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="Test", id_agencia=2, nombre_agencia="MATRIZ",
        fecha_sistema=datetime(2026, 11, 6),
    ))


def request(**cambios):
    return DepositosYRetirosDiariosRequest(**{
        "fecha_inicio": "2026-11-01", "fecha_fin": "2026-11-06", **cambios,
    })


def fila(**cambios):
    return dict(
        codigo_usuario="ana", nombre_asesor="Ana", id_agencia=2, agencia="MATRIZ",
        codigo_producto="002", producto_ahorro="Ahorro Vista", fecha=date(2026, 11, 1),
        id_transaccion=7, tipo_transaccion="TRANSFERENCIAS ENTRE CUENTAS",
        depositos=Decimal("100.10"), retiros=Decimal("20.20"),
    ) | cambios


class Fuente:
    def __init__(self, filas=None, fecha=date(2026, 11, 6)):
        self.corte = CorteDepositosYRetiros(fecha, filas if filas is not None else [fila()])
        self.calls = []

    def obtener_diario(self, **kwargs):
        self.calls.append(kwargs)
        return self.corte

    def obtener_nombre_agencia(self, id_agencia):
        return "MATRIZ" if id_agencia == 2 else None


def test_pivota_dos_montos_por_dia_sin_acumular_y_completa_ceros():
    fuente = Fuente([
        fila(), fila(depositos=Decimal("0.20"), retiros=Decimal("0.10")),
        fila(fecha=datetime(2026, 11, 6), depositos=Decimal("30.30"), retiros=0),
    ])
    respuesta = DepositosYRetirosDiariosService(fuente, fuente).obtener(request(), auth())
    assert respuesta.dias == [date(2026, 11, d) for d in range(1, 7)]
    assert [v.model_dump() for v in respuesta.filas[0].valores] == [
        {"depositos": 100.3, "retiros": 20.3, "transacciones": [
            {"id_transaccion": 7, "tipo_transaccion": "TRANSFERENCIAS ENTRE CUENTAS", "valor": 100.3, "es_debito": False},
            {"id_transaccion": 7, "tipo_transaccion": "TRANSFERENCIAS ENTRE CUENTAS", "valor": 20.3, "es_debito": True},
        ]},
        *[{"depositos": 0, "retiros": 0, "transacciones": []} for _ in range(4)],
        {"depositos": 30.3, "retiros": 0, "transacciones": [
            {"id_transaccion": 7, "tipo_transaccion": "TRANSFERENCIAS ENTRE CUENTAS", "valor": 30.3, "es_debito": False},
        ]},
    ]
    assert fuente.calls == [{
        "fecha_inicio": date(2026, 11, 1), "fecha_fin": date(2026, 11, 6),
        "id_agencia": 0, "fecha_sistema": date(2026, 11, 6),
    }]


def test_no_mezcla_usuarios_con_igual_nombre_agencias_o_productos_y_permita_filtro_local():
    fuente = Fuente([
        fila(), fila(codigo_usuario="otra"), fila(id_agencia=17, agencia="SUR"),
        fila(codigo_producto="005", producto_ahorro="Cuenta Básica"),
    ])
    respuesta = DepositosYRetirosDiariosService(fuente, fuente).obtener(request(), auth())
    assert len(respuesta.filas) == 4
    assert sum(f.valores[0].depositos for f in respuesta.filas) == pytest.approx(400.4)
    basicas = [f for f in respuesta.filas if f.codigo_producto == "005"]
    assert len(basicas) == 1
    assert basicas[0].producto_ahorro == "Cuenta Básica"
    assert basicas[0].valores[0].retiros == 20.2
    assert len(fuente.calls) == 1


def test_fechas_fuera_del_rango_o_posteriores_al_corte_no_generan_flujos():
    fuente = Fuente([
        fila(fecha=date(2026, 10, 31)), fila(fecha=date(2026, 11, 7)),
        fila(fecha=date(2026, 11, 6)), fila(fecha=date(2026, 11, 5)),
    ], fecha=date(2026, 11, 5))
    respuesta = DepositosYRetirosDiariosService(fuente, fuente).obtener(request(id_agencia=2), auth())
    assert respuesta.fecha_corte == date(2026, 11, 5)
    assert len(respuesta.filas) == 1
    assert respuesta.filas[0].valores[4].depositos == 100.1
    assert respuesta.filas[0].valores[5].depositos == 0
    assert fuente.calls[0]["id_agencia"] == 2


def test_un_dia_y_sin_movimientos_conservan_calendario():
    fuente = Fuente([])
    respuesta = DepositosYRetirosDiariosService(fuente, fuente).obtener(
        request(fecha_inicio="2026-11-06"), auth(),
    )
    assert respuesta.dias == [date(2026, 11, 6)]
    assert respuesta.filas == []


@pytest.mark.parametrize("cambios", [
    {"fecha_inicio": "2026-11-07"}, {"fecha_inicio": "2026-10-31"},
    {"id_agencia": -1}, {"productos": ["002"]}, {"cargos": []},
    {"fecha_fin": "9999-12-31"}, {"fecha_inicio": "1899-12-31"},
])
def test_request_rechaza_rango_invalido_y_filtros_que_son_locales(cambios):
    with pytest.raises(ValidationError):
        request(**cambios)


@pytest.mark.parametrize("cambios,status", [({"fecha_fin": "2026-11-07"}, 400), ({"id_agencia": 99}, 404)])
def test_fecha_futura_o_agencia_inexistente_no_consultan_movimientos(cambios, status):
    fuente = Fuente()
    with pytest.raises(HTTPException) as error:
        DepositosYRetirosDiariosService(fuente, fuente).obtener(request(**cambios), auth())
    assert error.value.status_code == status
    assert fuente.calls == []


def test_cierre_faltante_no_se_confunde_con_cero():
    fuente = Fuente()
    fuente.corte = None
    with pytest.raises(HTTPException) as error:
        DepositosYRetirosDiariosService(fuente, fuente).obtener(request(), auth())
    assert error.value.status_code == 404


def test_endpoint_bearer_contrato_y_sin_dialogo_de_operaciones():
    client = TestClient(app)
    body = request().model_dump(mode="json")
    assert client.post(URL, json=body).status_code == 401
    fuente = Fuente()
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_depositos_y_retiros_diarios_service] = lambda: DepositosYRetirosDiariosService(fuente, fuente)
    try:
        response = client.post(URL, json=body)
        assert response.status_code == 200
        data = response.json()
        assert data["dias"] == [f"2026-11-0{d}" for d in range(1, 7)]
        dia = data["filas"][0]["valores"][0]
        assert dia["depositos"] == 100.1
        assert dia["retiros"] == 20.2
        assert dia["transacciones"] == [
            {"id_transaccion": 7, "tipo_transaccion": "TRANSFERENCIAS ENTRE CUENTAS", "valor": 100.1, "es_debito": False},
            {"id_transaccion": 7, "tipo_transaccion": "TRANSFERENCIAS ENTRE CUENTAS", "valor": 20.2, "es_debito": True},
        ]
        assert data["filas"][0]["codigo_producto"] == "002"
        assert "cargo" not in data["filas"][0]
        assert client.post(URL, json=body | {"productos": []}).status_code == 422
        assert client.post(URL + "/detalle", json=body).status_code == 404
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
        return Resultado(row=self.corte) if len(self.calls) == 1 else Resultado()


@pytest.mark.parametrize("fecha,cerrado,fuente_viva", [
    (date(2026, 11, 6), False, True), (date(2026, 11, 5), True, False),
    (date(2026, 11, 6), True, False),
])
def test_cuentas_al_corte_y_token_viejo_no_reemplazan_historia(fecha, cerrado, fuente_viva):
    db = SessionFake({"fecha": datetime.combine(fecha, datetime.min.time()), "cerrado": cerrado,
                      "cierre": datetime(2026, 11, 6, 3) if cerrado else None})
    resultado = SqlDepositosYRetirosDiariosRepository(db).obtener_diario(
        fecha_inicio=date(2026, 11, 1), fecha_fin=fecha,
        fecha_sistema=date(2026, 11, 6), id_agencia=2,
    )
    assert resultado.fecha == fecha
    sql, params = db.calls[1]
    assert ("FOR SYSTEM_TIME AS OF :cierre" in sql) != fuente_viva
    assert "AND CU.IDAGENCIA = :id_agencia" in sql
    assert params["hasta_exclusivo"] == fecha.fromordinal(fecha.toordinal() + 1)
    assert params["id_agencia"] == 2


@pytest.mark.parametrize("corte", [None, {"fecha": date(2026, 11, 5), "cerrado": True, "cierre": None}])
def test_sql_no_usa_datos_actuales_cuando_falta_el_cierre(corte):
    db = SessionFake(corte)
    assert SqlDepositosYRetirosDiariosRepository(db).obtener_diario(
        fecha_inicio=date(2026, 11, 1), fecha_fin=date(2026, 11, 5),
        fecha_sistema=date(2026, 11, 6), id_agencia=0,
    ) is None
    assert len(db.calls) == 1


class LibroSqlite:
    """Ejecuta el SELECT real; adapta solo literal Unicode, fecha y metadatos TOP."""

    def __init__(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.calls = []
        for schema in ("FINANCIERO", "AHORROS", "GENERAL", "SEGURIDAD"):
            self.connection.execute(f"ATTACH DATABASE ':memory:' AS {schema}")
        self.connection.executescript("""
            CREATE TABLE FINANCIERO.MOVIMIENTO_TRANSACCION (ID int, IDTRANSACCION int, FECHASISTEMA text);
            CREATE TABLE FINANCIERO.TRANSACCION (ID int PRIMARY KEY, NOMBRE text);
            CREATE TABLE FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE (ID int, IDMOVIMIENTOTRANSACCION int, DEBITO int, VALOR numeric);
            CREATE TABLE FINANCIERO.MOVIMIENTO_TRANSACCION_REVERSO (IDMOVIMIENTO int, IDMOVIMIENTOREVERSO int);
            CREATE TABLE AHORROS.CUENTA_MOVIMIENTOTRANSACCIONDETALLE (IDMOVIMIENTOTRANSACCIONDETALLE int, NUMEROCUENTA text);
            CREATE TABLE AHORROS.CUENTA (NUMERO text, IDAGENCIA int, CODIGOUSUARIOOFICIAL text, CODIGOTIPOCUENTA text);
            CREATE TABLE AHORROS.TIPO_CUENTA (CODIGO text, NOMBRE text, ESPROGRAMADO int);
            CREATE TABLE GENERAL.AGENCIA (ID int, NOMBRE text);
            CREATE TABLE SEGURIDAD.USUARIO (USUARIO text, NOMBRE text);
            INSERT INTO AHORROS.TIPO_CUENTA VALUES ('001','Aportación',0),('002','Vista',0),('004','Programado',1),('005','Básica',0);
            INSERT INTO AHORROS.CUENTA VALUES ('vista',2,'ana','002'),('basica',2,'ana','005'),('otra',17,'ana','002'),('programada',2,'ana','004'),('aporte',2,'ana','001');
            INSERT INTO GENERAL.AGENCIA VALUES (2,'MATRIZ'),(17,'SUR');
            INSERT INTO SEGURIDAD.USUARIO VALUES ('ana','Ana');
            INSERT INTO FINANCIERO.TRANSACCION VALUES (2,'DEPOSITO'),(3,'RETIRO'),(7,'TRANSFERENCIAS ENTRE CUENTAS');
        """)
        self.next_id = 1

    def movimiento(self, tipo=2, dia="2026-11-01", debito=0, valor=10, cuenta="vista", id_movimiento=None):
        id_detalle = self.next_id
        self.next_id += 1
        id_movimiento = id_movimiento or id_detalle
        if not self.connection.execute("SELECT 1 FROM FINANCIERO.MOVIMIENTO_TRANSACCION WHERE ID=?", (id_movimiento,)).fetchone():
            self.connection.execute("INSERT INTO FINANCIERO.MOVIMIENTO_TRANSACCION VALUES (?,?,?)", (id_movimiento, tipo, dia))
        self.connection.execute("INSERT INTO FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE VALUES (?,?,?,?)", (id_detalle, id_movimiento, debito, valor))
        self.connection.execute("INSERT INTO AHORROS.CUENTA_MOVIMIENTOTRANSACCIONDETALLE VALUES (?,?)", (id_detalle, cuenta))
        return id_movimiento

    def execute(self, statement, params):
        self.calls.append((str(statement), params))
        if "CALENDARIO_SISTEMA" in str(statement):
            return Resultado(row={"fecha": date(2026, 11, 6), "cerrado": False, "cierre": None})
        compiled = statement.params(**params).compile(dialect=sqlite.dialect(), compile_kwargs={"render_postcompile": True})
        sql = str(compiled).replace("N'", "'").replace("CAST(MT.FECHASISTEMA AS date)", "DATE(MT.FECHASISTEMA)")
        parameters = [compiled.params[name] for name in compiled.positiontup]
        parameters = [value.isoformat() if isinstance(value, date) else value for value in parameters]
        return Resultado(rows=[dict(r) for r in self.connection.execute(sql, parameters)])


@pytest.fixture
def libro():
    db = LibroSqlite()
    yield db
    db.connection.close()


def consultar(libro, agencia=0):
    return SqlDepositosYRetirosDiariosRepository(libro).obtener_diario(
        fecha_inicio=date(2026, 11, 1), fecha_fin=date(2026, 11, 6),
        fecha_sistema=date(2026, 11, 6), id_agencia=agencia,
    ).filas


def test_sql_incluye_cualquier_tipo_que_agregue_o_quite_saldo(libro):
    for tipo in (2, 2113):
        libro.movimiento(tipo=tipo, valor=10, cuenta="basica" if tipo == 2113 else "vista")
    for tipo in (3, 4, 2091, 2100):
        libro.movimiento(tipo=tipo, debito=1, valor=5)
    for tipo in (1, 5, 35, 45, 99999):
        libro.movimiento(tipo=tipo, valor=3)
    for tipo in (6, 7, 30, 36, 43):
        libro.movimiento(tipo=tipo, debito=1, valor=2)
    filas = consultar(libro)
    assert sum(f["depositos"] for f in filas) == 35
    assert sum(f["retiros"] for f in filas) == 30
    assert {f["codigo_producto"] for f in filas} == {"002", "005"}


def test_sql_excluye_operaciones_internas_con_saldo_neto_cero(libro):
    for tipo in (33, 34, 2093, 99999):
        movimiento = libro.movimiento(tipo=tipo, valor=100)
        libro.movimiento(tipo=tipo, valor=100, debito=1, id_movimiento=movimiento)
    libro.movimiento(valor=0)
    assert consultar(libro) == []


def test_sql_usa_variacion_real_y_no_el_importe_bruto_de_los_detalles(libro):
    entrada = libro.movimiento(tipo=5, valor=150)
    libro.movimiento(tipo=5, debito=1, valor=50, id_movimiento=entrada)
    salida = libro.movimiento(tipo=6, debito=1, valor=75)
    libro.movimiento(tipo=6, valor=25, id_movimiento=salida)
    filas = consultar(libro)
    assert {f["id_transaccion"]: (f["depositos"], f["retiros"]) for f in filas} == {
        5: (100, 0), 6: (0, 50),
    }


def test_sql_no_compensa_operaciones_distintas_del_mismo_dia(libro):
    libro.movimiento(valor=100)
    libro.movimiento(tipo=3, debito=1, valor=100)
    filas = consultar(libro)
    assert sum(f["depositos"] for f in filas) == 100
    assert sum(f["retiros"] for f in filas) == 100


def test_sql_transferencia_no_compensa_cuentas_distintas_de_la_misma_operacion(libro):
    movimiento = libro.movimiento(tipo=7, debito=1, valor=75, cuenta="vista")
    libro.movimiento(tipo=7, valor=75, cuenta="otra", id_movimiento=movimiento)
    filas = {f["id_agencia"]: f for f in consultar(libro)}
    assert filas[2]["depositos"] == 0
    assert filas[2]["retiros"] == 75
    assert filas[17]["depositos"] == 75
    assert filas[17]["retiros"] == 0


def test_sql_reversos_excluye_ambos_lados_y_conserva_original_revertido_despues_del_corte(libro):
    original = libro.movimiento(valor=100)
    reverso = libro.movimiento(tipo=2, dia="2026-11-02", debito=1, valor=100)
    libro.connection.execute("INSERT INTO FINANCIERO.MOVIMIENTO_TRANSACCION_REVERSO VALUES (?,?)", (original, reverso))
    valido_al_corte = libro.movimiento(valor=40)
    futuro = libro.movimiento(tipo=2, dia="2026-11-07", debito=1, valor=40)
    libro.connection.execute("INSERT INTO FINANCIERO.MOVIMIENTO_TRANSACCION_REVERSO VALUES (?,?)", (valido_al_corte, futuro))
    fuera_rango = libro.movimiento(dia="2026-10-31", valor=70)
    reverso_en_rango = libro.movimiento(tipo=2, dia="2026-11-03", debito=1, valor=70)
    libro.connection.execute("INSERT INTO FINANCIERO.MOVIMIENTO_TRANSACCION_REVERSO VALUES (?,?)", (fuera_rango, reverso_en_rango))
    filas = consultar(libro)
    assert sum(f["depositos"] for f in filas) == 40
    assert sum(f["retiros"] for f in filas) == 0


def test_sql_atribuye_a_cuenta_filtra_agencia_y_excluye_programados_aportaciones(libro):
    for cuenta in ("vista", "otra", "basica", "programada", "aporte"):
        libro.movimiento(cuenta=cuenta)
    filas = consultar(libro, agencia=2)
    assert sum(f["depositos"] for f in filas) == 20
    assert {f["id_agencia"] for f in filas} == {2}
    assert {f["codigo_usuario"] for f in filas} == {"ana"}
    assert {f["codigo_producto"] for f in filas} == {"002", "005"}


def test_sql_suma_detalles_una_vez_y_respeta_extremos_inclusivos(libro):
    libro.movimiento(dia="2026-10-31 23:59:59", valor=999)
    movimiento = libro.movimiento(dia="2026-11-01 00:00:00", valor=10)
    libro.movimiento(valor=15, id_movimiento=movimiento)
    libro.movimiento(dia="2026-11-06 23:59:59", valor=20)
    libro.movimiento(dia="2026-11-07 00:00:00", valor=999)
    filas = consultar(libro)
    assert {f["fecha"]: f["depositos"] for f in filas} == {"2026-11-01": 25, "2026-11-06": 20}


def test_desglose_diario_conserva_tipo_sentido_y_totales_desde_el_sql(libro):
    libro.movimiento(tipo=2, valor=10)
    libro.movimiento(tipo=2, valor=15)
    libro.movimiento(tipo=7, valor=40)
    libro.movimiento(tipo=7, debito=1, valor=40)
    libro.movimiento(tipo=3, debito=1, valor=5)
    # El sentido se deriva de la cuenta, aunque el nombre diga RETIRO.
    libro.movimiento(tipo=3, dia="2026-11-02", valor=8)
    # No perder movimientos por un nombre de catálogo ausente.
    libro.movimiento(tipo=99999, valor=3)
    filas = [dict(f, fecha=date.fromisoformat(f["fecha"])) for f in consultar(libro)]
    fuente = Fuente(filas)
    respuesta = DepositosYRetirosDiariosService(fuente, fuente).obtener(request(), auth())
    dia = respuesta.filas[0].valores[0]
    assert (dia.depositos, dia.retiros) == (68, 45)
    assert [(t.id_transaccion, t.es_debito, t.valor) for t in dia.transacciones] == [
        (2, False, 25), (3, True, 5), (7, False, 40), (7, True, 40), (99999, False, 3),
    ]
    assert dia.transacciones[0].tipo_transaccion == "DEPOSITO"
    assert dia.transacciones[-1].tipo_transaccion == "99999"
    siguiente = respuesta.filas[0].valores[1]
    assert [(t.id_transaccion, t.es_debito, t.valor) for t in siguiente.transacciones] == [(3, False, 8)]
    for fila_diaria in respuesta.filas:
        for valor in fila_diaria.valores:
            assert all(t.valor > 0 for t in valor.transacciones)
            assert sum(t.valor for t in valor.transacciones if not t.es_debito) == pytest.approx(valor.depositos)
            assert sum(t.valor for t in valor.transacciones if t.es_debito) == pytest.approx(valor.retiros)


class SesionConDeadlocks:
    def __init__(self, etapa="movimientos", fallos=1, original=None):
        self.etapa = etapa
        self.fallos = fallos
        self.original = original or Exception("40001", "Transaction was deadlocked. (1205) (SQLExecDirectW)")
        self.eventos = []

    def _fallar(self):
        if self.fallos:
            self.fallos -= 1
            raise DBAPIError("SELECT", {}, self.original)

    def execute(self, statement, params):
        etapa = "corte" if "CALENDARIO_SISTEMA" in str(statement) else "movimientos"
        self.eventos.append(etapa)
        if etapa == self.etapa:
            self._fallar()
        if etapa == "corte":
            return Resultado(row={"fecha": date(2026, 11, 6), "cerrado": False, "cierre": None})
        if self.etapa == "fetch":
            db = self

            class Lectura(Resultado):
                def all(self):
                    db._fallar()
                    return [fila()]

            return Lectura()
        return Resultado(rows=[fila()])

    def rollback(self):
        self.eventos.append("rollback")


@pytest.fixture
def esperas_deadlock(monkeypatch):
    esperas = []
    monkeypatch.setattr(diario_sql.time, "sleep", esperas.append)
    return esperas


@pytest.mark.parametrize("etapa", ["corte", "movimientos", "fetch"])
def test_deadlock_reinicia_lectura_completa_con_rollback_y_espera(etapa, esperas_deadlock):
    db = SesionConDeadlocks(etapa=etapa, fallos=2)
    resultado = diario_sql.SqlDepositosYRetirosDiariosRepository(db).obtener_diario(
        **request().model_dump(), fecha_sistema=date(2026, 11, 6),
    )
    assert resultado.filas == [fila()]
    assert db.eventos.count("corte") == 3
    assert db.eventos.count("rollback") == 2
    assert all(db.eventos[i + 1] == "corte" for i, e in enumerate(db.eventos) if e == "rollback")
    assert len(esperas_deadlock) == 2
    assert 0.2 <= esperas_deadlock[0] <= 0.5
    assert 0.4 <= esperas_deadlock[1] <= 1


@pytest.mark.parametrize("original", [
    Exception("40001", "Serialization conflict without native deadlock code"),
    Exception("HYT00", "Timeout expired (0)"),
    Exception("42000", "Invalid column name (207)"),
])
def test_otros_errores_sql_no_se_reintentan(original, esperas_deadlock):
    db = SesionConDeadlocks(original=original)
    with pytest.raises(DBAPIError) as error:
        diario_sql.SqlDepositosYRetirosDiariosRepository(db).obtener_diario(
            **request().model_dump(), fecha_sistema=date(2026, 11, 6),
        )
    assert error.value.orig is original
    assert db.eventos == ["corte", "movimientos"]
    assert esperas_deadlock == []


def test_endpoint_deadlock_persistente_devuelve_503_con_reintentos_acotados(esperas_deadlock):
    db = SesionConDeadlocks(fallos=10)
    servicio = DepositosYRetirosDiariosService(diario_sql.SqlDepositosYRetirosDiariosRepository(db), Fuente())
    app.dependency_overrides[get_current_auth_context] = auth
    app.dependency_overrides[get_depositos_y_retiros_diarios_service] = lambda: servicio
    try:
        response = TestClient(app).post(URL, json=request().model_dump(mode="json"))
        assert response.status_code == 503
        assert response.headers["Retry-After"] == "2"
        assert "conflicto temporal de bloqueos" in response.json()["detail"]
        assert db.eventos == ["corte", "movimientos", "rollback"] * 3
        assert len(esperas_deadlock) == 2
    finally:
        app.dependency_overrides.clear()
