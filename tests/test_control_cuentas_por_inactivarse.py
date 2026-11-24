from datetime import date, datetime, timedelta
from sqlite3 import connect

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects.mssql import pyodbc

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.cuentas.control_cuentas_por_inactivarse.dependencies import (
    get_control_cuentas_por_inactivarse_service,
)
from app.modules.negocios.cuentas.control_cuentas_por_inactivarse.repositories.sql_control_cuentas_por_inactivarse_repository import (
    SqlControlCuentasPorInactivarseRepository,
    _cuentas_candidatas,
)
from app.modules.negocios.cuentas.control_cuentas_por_inactivarse.service import (
    ControlCuentasPorInactivarseService,
)


URL = "/negocios/cuentas/control-de-cuentas-por-inactivarse"
FECHA_SISTEMA = date(2026, 11, 24)


@pytest.fixture
def cliente():
    class Fuente:
        def obtener_desglose(self, ids_agencia, **filtros):
            assert ids_agencia == [2, 17]
            assert filtros == dict(fecha_sistema=FECHA_SISTEMA, plazos=["0_7", "cumplido"], saldo="con_saldo")
            return [
                dict(
                    id_agencia=id_agencia, agencia=f"Agencia {id_agencia}", cargo="CAPTADOR",
                    codigo_oficial="oficial-1", oficial="Oficial", codigo_tipo_cuenta="002",
                    tipo_cuenta="Ahorro Vista", cantidad_cuentas=1,
                    valor_disponible="0.000001", valor_total="12.123456",
                )
                for id_agencia in ids_agencia
            ]

        def obtener_gerentes_oficina(self, agencias):
            assert agencias == {"Agencia 2", "Agencia 17"}
            return [dict(IdAgencia=2, Cargo="Jefe de agencia", GerenteOficina="Responsable")]

        def obtener_detalle(self, **filtros):
            assert filtros == dict(
                ids_agencia=[2], fecha_sistema=FECHA_SISTEMA, plazos=["0_7", "cumplido"],
                saldo="con_saldo", cargos=["CAPTADOR"], asesores=["oficial-1"],
                codigo_oficial="oficial-1", codigo_tipo_cuenta="002",
                pagina=1, tamano_pagina=25, sin_paginacion=True,
            )
            return 1, [dict(
                numero_cuenta="001", agencia="Agencia 2", oficial="Oficial", titular=None,
                tipo_cuenta="Ahorro Vista", ultima_transaccion_activa=date(2025, 11, 28),
                fecha_cumplimiento=FECHA_SISTEMA, dias_restantes=0,
                valor_disponible="0.000001", valor_total="12.123456",
            )]

    fuente = Fuente()
    auth = AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="prueba", id_agencia=2, fecha_sistema=FECHA_SISTEMA,
    ))
    app.dependency_overrides[get_current_auth_context] = lambda: auth
    app.dependency_overrides[get_control_cuentas_por_inactivarse_service] = (
        lambda: ControlCuentasPorInactivarseService(fuente, fuente)
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_auth_context)
        app.dependency_overrides.pop(get_control_cuentas_por_inactivarse_service)


def test_resumen_y_detalle_del_nuevo_control(cliente):
    filtros = {"plazos": ["0_7", "cumplido"], "saldo": "con_saldo"}
    resumen = cliente.post(URL, json={**filtros, "id_agencia": 0, "ids_agencia": [17, 2, 17]})
    assert resumen.status_code == 200
    data = resumen.json()
    assert data["fecha_sistema"] == FECHA_SISTEMA.isoformat()
    assert data["resumen"][0]["nombre_jefe_agencia"] == "Responsable"
    assert data["total"] == dict(cantidad_cuentas=2, valor_disponible="0.000002", valor_total="24.246912")

    detalle = cliente.post(URL + "/detalle", json={
        **filtros, "id_agencia": 2, "cargos": ["CAPTADOR"], "asesores": ["oficial-1"],
        "codigo_oficial": "oficial-1", "codigo_tipo_cuenta": "002", "sin_paginacion": True,
    })
    assert detalle.status_code == 200
    data = detalle.json()
    assert data["pagina"] is None and data["tamano_pagina"] is None
    assert data["total_registros"] == 1
    assert data["filas"][0]["fecha_cumplimiento"] == FECHA_SISTEMA.isoformat()
    assert data["filas"][0]["dias_restantes"] == 0
    assert "fecha_inactivacion" not in data["filas"][0]

    assert cliente.post(URL, json={"id_agencia": 0}).status_code == 422
    assert cliente.post(URL, json={"id_agencia": 2, "plazos": ["3_6"]}).status_code == 422


def test_candidatas_aplican_plazo_por_tipo_y_limites_del_multiselect():
    with connect(":memory:") as db:
        db.execute("ATTACH DATABASE ':memory:' AS AHORROS")
        db.execute("ATTACH DATABASE ':memory:' AS GENERAL")
        db.execute("CREATE TABLE GENERAL.MONEDA (ID INTEGER, CODIGO TEXT)")
        db.execute("INSERT INTO GENERAL.MONEDA VALUES (1, 'USD'), (2, 'EUR')")
        db.execute("CREATE TABLE AHORROS.TIPO_CUENTA (CODIGO TEXT, NOMBRE TEXT, ESCERTIFICADOAPORTACION INTEGER)")
        db.execute("INSERT INTO AHORROS.TIPO_CUENTA VALUES ('002', 'Vista', 0), ('003', 'Programado', 0), ('004', 'Sin plazo', 0)")
        db.execute("CREATE TABLE AHORROS.TIPO_CUENTA_DIASINACTIVA (CODIGOTIPOCUENTA TEXT, DIASINACTIVIDAD INTEGER)")
        db.execute("INSERT INTO AHORROS.TIPO_CUENTA_DIASINACTIVA VALUES ('002', 360), ('003', 90)")
        db.execute("""
            CREATE TABLE AHORROS.CUENTA (
                NUMERO TEXT, IDAGENCIA INTEGER, IDMONEDA INTEGER, CODIGOESTADO TEXT,
                CODIGOTIPOCUENTA TEXT, CODIGOUSUARIOOFICIAL TEXT, FECHAULTIMATRANSACCIONACTIVA TEXT
            )
        """)
        for dias in (-1, 0, 7, 8, 15, 16, 30, 31):
            actividad = FECHA_SISTEMA + timedelta(days=dias - 361)
            db.execute("INSERT INTO AHORROS.CUENTA VALUES (?, 2, 1, 'A', '002', 'O', ?)", (
                str(dias), actividad.isoformat() + " 23:59:59",
            ))
        db.execute("""
            INSERT INTO AHORROS.CUENTA VALUES
            ('por_tipo', 2, 1, 'A', '003', 'O', date(:hoy, '-91 days')),
            ('sin_fecha', 2, 1, 'A', '002', 'O', NULL),
            ('sin_configuracion', 2, 1, 'A', '004', 'O', date(:hoy, '-400 days')),
            ('inactiva', 2, 1, 'I', '002', 'O', date(:hoy, '-400 days')),
            ('otra_agencia', 3, 1, 'A', '002', 'O', date(:hoy, '-400 days')),
            ('otra_moneda', 2, 2, 'A', '002', 'O', date(:hoy, '-400 days'))
        """, {"hoy": FECHA_SISTEMA.isoformat()})
        db.create_function("DATEADD_DAY", 2, lambda dias, desde: (
            (datetime.fromisoformat(desde).date() + timedelta(days=dias)).isoformat()
            if desde is not None else None
        ))

        def consultar(plazos):
            params = {"agencia": 2}
            sql = _cuentas_candidatas(params, FECHA_SISTEMA, plazos)
            # SQLite requiere sustituir APPLY y las operaciones de fecha de SQL Server.
            inicio = sql.index("        CROSS APPLY")
            fin = sql.index("AS P(fecha_cumplimiento)", inicio) + len("AS P(fecha_cumplimiento)")
            expresion = sql[inicio:fin].split("VALUES (", 1)[1].rsplit(")) AS P", 1)[0]
            expresion = expresion.replace("DATEADD(day,", "DATEADD_DAY(").replace(
                "CAST(C.FECHAULTIMATRANSACCIONACTIVA AS date)", "date(C.FECHAULTIMATRANSACCIONACTIVA)",
            )
            sql = (sql[:inicio] + sql[fin:]).replace("P.fecha_cumplimiento", expresion + " AS fecha_cumplimiento", 1)
            sql = sql.replace("P.fecha_cumplimiento", expresion)
            sql = sql.replace("IN :ids_agencia", "= :agencia").replace("N'A'", "'A'").replace("N'USD'", "'USD'")
            params = {
                nombre: valor.isoformat() if isinstance(valor, date) else valor
                for nombre, valor in params.items()
            }
            return dict(db.execute(
                f"WITH {sql} SELECT NUMERO, fecha_cumplimiento FROM CuentasCandidatas", params,
            ))

        assert consultar(["0_7"]) == {"0": "2026-11-24", "7": "2026-12-01", "por_tipo": "2026-11-24"}
        assert set(consultar(["8_15", "cumplido"])) == {"8", "15", "-1"}
        assert set(consultar(["16_30"])) == {"16", "30"}
        assert set(consultar([])) == {"-1", "0", "7", "8", "15", "16", "30", "por_tipo"}


def test_detalle_compila_con_filtros_parametrizados_en_una_consulta():
    class Sesion:
        def __init__(self):
            self.consultas = []

        def execute(self, consulta, parametros):
            compilada = consulta.params(**parametros).compile(
                dialect=pyodbc.dialect(paramstyle="qmark"),
                compile_kwargs={"render_postcompile": True},
            )
            self.consultas.append((str(compilada), compilada.params))
            return self

        def mappings(self):
            return self

        def all(self):
            return []

    db = Sesion()
    repo = SqlControlCuentasPorInactivarseRepository(db)
    total, filas = repo.obtener_detalle(
        ids_agencia=[2, 17], fecha_sistema=FECHA_SISTEMA, plazos=["0_7", "cumplido"], saldo="con_saldo",
        cargos=["CAPTADOR"], asesores=["oficial-1"], codigo_oficial="oficial-1", codigo_tipo_cuenta="002",
        pagina=1, tamano_pagina=25, sin_paginacion=True,
    )
    assert total == 0 and filas == []
    (sql, params), = db.consultas
    assert "DATEDIFF(day, ?, C.fecha_cumplimiento) AS dias_restantes" in sql
    assert "ROUND(COALESCE(S.total, 0), 2) <> 0" in sql
    assert sql.count("FROM AHORROS.CUENTA_ITEMSALDO AS CI") == 1
    assert "OFFSET" not in sql and "CUENTAESTADO_HISTORICO" not in sql
    assert params["cargos_1"] == "CAPTADOR"
    assert params["asesores_1"] == "oficial-1"
    assert params["codigo_tipo_cuenta"] == "002"
    assert params["desde_0"] == FECHA_SISTEMA
    assert params["hasta_0"] == date(2026, 12, 1)
    assert params["hasta_1"] == date(2026, 11, 23)
