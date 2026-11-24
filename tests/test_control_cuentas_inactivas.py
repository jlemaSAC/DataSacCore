from datetime import date
from sqlite3 import connect

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.cuentas.control_cuentas_inactivas.dependencies import (
    get_control_cuentas_inactivas_service,
)
from app.modules.negocios.cuentas.control_cuentas_inactivas.repositories.sql_control_cuentas_inactivas_repository import (
    _HISTORIAL_INACTIVACION,
    _PREDICADOS_SALDO,
    _filtro_cuentas,
    SqlControlCuentasInactivasRepository,
)
from app.modules.negocios.cuentas.control_cuentas_inactivas.service import (
    ControlCuentasInactivasService,
)


URL = "/negocios/cuentas/control-cuentas-inactivas"


class Fuente:
    def __init__(self):
        self.consultas = []

    def obtener_gerentes_oficina(self, agencias):
        assert agencias == {"Agencia de prueba"}
        return [
            {"IdAgencia": 17, "Cargo": "JEFE DE AGENCIA", "GerenteOficina": "Responsable de prueba"}
        ]

    def obtener_desglose(self, ids_agencia, **filtros):
        self.consultas.append(dict(ids_agencia=ids_agencia, **filtros))
        base = dict(
            agencia="Agencia de prueba",
            oficial="Oficial", cargo="CAPTADOR", codigo_tipo_cuenta="002", tipo_cuenta="Ahorro Vista",
            cantidad_cuentas=1, valor_disponible="0.10", valor_total="0.15",
        )
        filas = [
            dict(base, codigo_oficial="oficial-1"),
            dict(base, codigo_oficial="oficial-2", valor_disponible="0.20"),
        ]
        return [dict(fila, id_agencia=id_agencia) for id_agencia in ids_agencia for fila in filas]

    def obtener_detalle(self, **filtros):
        self.consultas.append(filtros)
        fila = dict(
            numero_cuenta="cuenta-26", agencia="Agencia de prueba", titular="Titular",
            oficial="Oficial", tipo_cuenta="Ahorro Vista",
            ultima_transaccion_activa=date(2020, 1, 1),
            fecha_inactivacion=date(2026, 10, 23), dias_inactividad=31,
            valor_disponible="0.10", valor_total="0.15",
        )
        if filtros["sin_paginacion"]:
            return 650, [dict(fila, numero_cuenta=str(i)) for i in range(650)]
        return 35, [fila]


@pytest.fixture
def cliente():
    fuente = Fuente()
    auth = AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="usuario-prueba", id_agencia=2, fecha_sistema=date(2026, 11, 23),
    ))
    app.dependency_overrides[get_current_auth_context] = lambda: auth
    app.dependency_overrides[get_control_cuentas_inactivas_service] = (
        lambda: ControlCuentasInactivasService(fuente, fuente)
    )
    try:
        yield TestClient(app), fuente
    finally:
        app.dependency_overrides.pop(get_current_auth_context)
        app.dependency_overrides.pop(get_control_cuentas_inactivas_service)


def test_resumen_consulta_y_acumula_por_agencia(cliente):
    client, fuente = cliente
    respuesta = client.post(URL, json={"id_agencia": 17})

    assert respuesta.status_code == 200
    assert fuente.consultas == [dict(
        ids_agencia=[17], fecha_sistema=date(2026, 11, 23), inactividad=None, saldo=None,
    )]
    data = respuesta.json()
    assert len(data["desglose"]) == 2
    agencia, = data["resumen"]
    assert agencia["id_agencia"] == 17
    assert agencia["cargo_jefe_agencia"] == "JEFE DE AGENCIA"
    assert agencia["nombre_jefe_agencia"] == "Responsable de prueba"
    assert agencia["cantidad_cuentas"] == 2
    assert agencia["valor_disponible"] == "0.30"
    assert agencia["valor_total"] == "0.30"
    assert data["total"] == {
        "cantidad_cuentas": 2, "valor_disponible": "0.30", "valor_total": "0.30",
    }


def test_detalle_conserva_el_alcance_de_la_fila_y_la_paginacion(cliente):
    client, fuente = cliente
    filtros = dict(
        id_agencia=17, codigo_oficial="oficial-1",
        codigo_tipo_cuenta="002", pagina=2, tamano_pagina=25,
    )
    respuesta = client.post(URL + "/detalle", json=filtros)

    assert respuesta.status_code == 200
    assert fuente.consultas == [dict(
        codigo_oficial="oficial-1", codigo_tipo_cuenta="002",
        pagina=2, tamano_pagina=25, ids_agencia=[17], fecha_sistema=date(2026, 11, 23),
        inactividad=None, saldo=None, cargos=[], asesores=[], sin_paginacion=False,
    )]
    data = respuesta.json()
    assert data["pagina"] == 2
    assert data["total_registros"] == 35
    assert data["filas"][0]["ultima_transaccion_activa"] == "2020-01-01"
    assert data["filas"][0]["fecha_inactivacion"] == "2026-10-23"
    assert data["filas"][0]["dias_inactividad"] == 31
    assert data["filas"][0]["agencia"] == "Agencia de prueba"


def test_consolidado_consulta_las_agencias_enviadas_y_mantiene_el_resumen_por_agencia(cliente):
    client, fuente = cliente
    respuesta = client.post(URL, json={"id_agencia": 0, "ids_agencia": [17, 2, 17]})

    assert respuesta.status_code == 200
    assert fuente.consultas == [dict(
        ids_agencia=[2, 17], fecha_sistema=date(2026, 11, 23), inactividad=None, saldo=None,
    )]
    data = respuesta.json()
    assert data["id_agencia"] == 0
    assert [fila["id_agencia"] for fila in data["resumen"]] == [2, 17]
    assert data["resumen"][0]["nombre_jefe_agencia"] is None
    assert data["total"] == {
        "cantidad_cuentas": 4, "valor_disponible": "0.60", "valor_total": "0.60",
    }


def test_detalle_del_total_consulta_las_agencias_del_consolidado(cliente):
    client, fuente = cliente
    respuesta = client.post(URL + "/detalle", json={
        "id_agencia": 0, "ids_agencia": [17, 2], "pagina": 2,
    })

    assert respuesta.status_code == 200
    assert fuente.consultas[0]["ids_agencia"] == [2, 17]
    assert fuente.consultas[0]["pagina"] == 2


@pytest.mark.parametrize("inactividad,saldo", [
    ("0_1", "cero"), ("3_6", "con_saldo"), ("sin_fecha", "cero"),
    (["3_6", "36_60", "mas_60"], "con_saldo"),
])
def test_resumen_y_detalle_aplican_los_mismos_filtros(cliente, inactividad, saldo):
    client, fuente = cliente
    filtros = dict(id_agencia=17, inactividad=inactividad, saldo=saldo)

    assert client.post(URL, json=filtros).status_code == 200
    assert client.post(URL + "/detalle", json=filtros).status_code == 200
    esperado = dict(
        ids_agencia=[17], fecha_sistema=date(2026, 11, 23), inactividad=inactividad, saldo=saldo,
    )
    assert fuente.consultas == [
        esperado, dict(esperado, codigo_oficial=None, codigo_tipo_cuenta=None, pagina=1, tamano_pagina=25, cargos=[], asesores=[], sin_paginacion=False),
    ]


def test_detalle_recibe_seleccion_multiple_de_cargos_y_asesores(cliente):
    client, fuente = cliente
    respuesta = client.post(URL + "/detalle", json={
        "id_agencia": 0, "ids_agencia": [2, 17],
        "cargos": ["CAPTADOR", "JEFE DE AGENCIA"], "asesores": ["oficial-1", "oficial-2"],
        "inactividad": "3_6", "saldo": "cero", "pagina": 2,
    })
    assert respuesta.status_code == 200
    filtros, = fuente.consultas
    assert filtros["cargos"] == ["CAPTADOR", "JEFE DE AGENCIA"]
    assert filtros["asesores"] == ["oficial-1", "oficial-2"]
    assert filtros["ids_agencia"] == [2, 17]
    assert filtros["pagina"] == 2


def test_cargos_y_asesores_se_filtran_antes_de_contar_y_paginar():
    from sqlalchemy.dialects.mssql import pyodbc

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

        def scalar_one(self):
            return 30

        def mappings(self):
            return self

        def all(self):
            return []

    db = Sesion()
    repo = SqlControlCuentasInactivasRepository(db)
    repo.obtener_desglose([2, 17], fecha_sistema=date(2026, 11, 24), inactividad=None, saldo=None)
    assert "AS cargo" in db.consultas[0][0]
    assert "ORDER BY E.FECHAPROCESO DESC, E.ID DESC" in db.consultas[0][0]
    repo.obtener_detalle(
        ids_agencia=[2, 17], codigo_oficial=None, codigo_tipo_cuenta=None,
        pagina=2, tamano_pagina=25, fecha_sistema=date(2026, 11, 24),
        inactividad="3_6", saldo="cero",
        cargos=["CAPTADOR", "SIN CARGO"], asesores=["oficial-1", "oficial-2"],
    )
    for sql, parametros in db.consultas[1:]:
        assert "N'SIN CARGO') IN (?, ?)" in sql
        assert "C.CODIGOUSUARIOOFICIAL IN (?, ?)" in sql
        assert parametros["cargos_1"] == "CAPTADOR"
        assert parametros["asesores_2"] == "oficial-2"
    pagina_sql = db.consultas[-1][0]
    assert pagina_sql.index("N'SIN CARGO') IN (?, ?)") < pagina_sql.index("OFFSET")


def test_api_devuelve_toda_la_seleccion_sin_limite_de_pagina(cliente):
    client, fuente = cliente
    respuesta = client.post(URL + "/detalle", json={
        "id_agencia": 0, "ids_agencia": [2, 17], "sin_paginacion": True,
        "inactividad": "3_6", "saldo": "cero",
        "cargos": ["CAPTADOR"], "asesores": ["oficial-1"],
    })
    assert respuesta.status_code == 200
    data = respuesta.json()
    assert data["pagina"] is None and data["tamano_pagina"] is None
    assert data["total_registros"] == len(data["filas"]) == 650
    assert len(fuente.consultas) == 1
    assert fuente.consultas[0]["sin_paginacion"] is True


def test_carga_completa_ejecuta_una_consulta_y_limita_el_historico_a_las_candidatas():
    from sqlalchemy.dialects.mssql import pyodbc

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
            return [{"numero_cuenta": str(i)} for i in range(650)]

    db = Sesion()
    total, filas = SqlControlCuentasInactivasRepository(db).obtener_detalle(
        ids_agencia=[2, 17], codigo_oficial="oficial-1", codigo_tipo_cuenta="002",
        pagina=1, tamano_pagina=25, fecha_sistema=date(2026, 11, 24),
        inactividad="3_6", saldo="cero", cargos=["CAPTADOR"],
        asesores=["oficial-1", "oficial-2"], sin_paginacion=True,
    )
    assert total == len(filas) == 650
    sql, parametros = db.consultas[0]
    assert len(db.consultas) == 1
    assert "COUNT_BIG" not in sql and "OFFSET" not in sql
    assert "INNER JOIN CuentasCandidatas AS ACTUAL" in sql
    assert sql.index("C.CODIGOUSUARIOOFICIAL IN (?, ?)") < sql.index("CambiosCuenta AS")
    assert "UI.FECHA >= ?" in sql and "UI.FECHA < ?" in sql
    assert sql.count("FROM AHORROS.CUENTA_ITEMSALDO AS CI") == 1
    assert parametros["codigo_oficial"] == "oficial-1"
    assert parametros["codigo_tipo_cuenta"] == "002"


def test_los_rangos_de_inactividad_no_se_solapan_y_se_combinan_con_el_saldo():
    with connect(":memory:") as db:
        db.execute("""
            CREATE TABLE cuentas (
                numero TEXT, fechaInactivacion TEXT,
                fechaUltimaTransaccionActiva TEXT DEFAULT '1999-01-01',
                total REAL, idAgencia INTEGER DEFAULT 2, codigoEstado TEXT DEFAULT 'I'
            )
        """)
        db.executemany("INSERT INTO cuentas(numero, fechaInactivacion, total) VALUES (?, ?, ?)", [
            ("reciente", "2026-11-23 17:00:00", 0),
            ("uno", "2026-10-23 23:59:59", 0),
            ("dos", "2026-09-23", 0),
            ("tres", "2026-08-23 23:59:59", 0.004),
            ("cuatro", "2026-07-23", -0.50),
            ("seis", "2026-05-23", 1),
            ("doce", "2025-11-23", 1),
            ("veinticuatro", "2024-11-23", 1),
            ("treinta_y_seis", "2023-11-23", 0),
            ("mas_de_treinta_y_seis", "2023-11-22 23:59:59", 1),
            ("sesenta", "2021-11-23", 1),
            ("mas_de_sesenta", "2021-11-22", 1),
            ("sin_fecha", None, 0),
            ("futura", "2026-11-24", 0),
        ])
        db.execute("ATTACH DATABASE ':memory:' AS AHORROS")
        db.execute("CREATE TABLE AHORROS.CUENTA AS SELECT * FROM cuentas")
        db.execute("""
            CREATE TABLE AHORROS.CUENTAESTADO_HISTORICO (
                ID INTEGER PRIMARY KEY, NUMEROCUENTA TEXT, CODIGOESTADOCAMBIO TEXT,
                FECHA TEXT, FECHAPROCESO TEXT
            )
        """)
        db.execute("""
            INSERT INTO AHORROS.CUENTAESTADO_HISTORICO (
                NUMEROCUENTA, CODIGOESTADOCAMBIO, FECHA, FECHAPROCESO
            )
            SELECT numero, 'A', fechaInactivacion, fechaInactivacion
            FROM cuentas WHERE fechaInactivacion IS NOT NULL
        """)
        # La misma cuenta tuvo una inactivación antigua y una reactivación.
        # Debe conservar la última entrada a I y no duplicar la cuenta.
        db.executemany("""
            INSERT INTO AHORROS.CUENTAESTADO_HISTORICO (
                NUMEROCUENTA, CODIGOESTADOCAMBIO, FECHA, FECHAPROCESO
            ) VALUES (?, ?, ?, ?)
        """, [
            ("tres", "A", "2019-01-01", "2019-01-02"),
            ("tres", "I", "2026-07-01", "2026-07-02"),
            ("tres", "I", "2026-09-01", "2026-09-02"),
            ("uno", "A", "2018-01-01", "2018-01-02"),
            ("uno", "I", "2020-01-01", "2020-01-02"),
        ])

        def consultar(inactividad, saldo=None):
            filtros, params = _filtro_cuentas([2], inactividad, date(2026, 11, 23))
            # Adaptar únicamente la lista de agencias y el literal de SQL Server.
            filtros = filtros.replace("N'I'", "'I'").replace("IN :ids_agencia", "= :id_agencia")
            historial = _HISTORIAL_INACTIVACION.replace("N'I'", "'I'").replace(
                "IN :ids_agencia", "= :id_agencia",
            )
            params = {
                k: v.isoformat() if isinstance(v, date) else v
                for k, v in params.items() if k != "ids_agencia"
            }
            filas = db.execute(f"""
                WITH {historial}
                SELECT C.numero
                FROM cuentas AS C
                LEFT JOIN UltimaInactivacion AS UI ON UI.NUMEROCUENTA = C.numero
                INNER JOIN cuentas AS S ON S.numero = C.numero
                CROSS JOIN (SELECT 0 AS ESCERTIFICADOAPORTACION) AS TC
                {filtros} {_PREDICADOS_SALDO[saldo]}
            """, dict(params, id_agencia=2)).fetchall()
            return {fila[0] for fila in filas}

        assert consultar("0_1") == {"reciente"}
        assert consultar("1_2") == {"uno"}
        assert consultar("2_3") == {"dos"}
        assert consultar("3_6") == {"tres", "cuatro"}
        assert consultar("6_12") == {"seis"}
        assert consultar("12_24") == {"doce"}
        assert consultar("24_36") == {"veinticuatro"}
        assert consultar("36_60") == {"treinta_y_seis", "mas_de_treinta_y_seis", "sesenta"}
        assert consultar("mas_60") == {"mas_de_sesenta"}
        assert consultar(["3_6", "36_60"]) == {
            "tres", "cuatro", "treinta_y_seis", "mas_de_treinta_y_seis", "sesenta",
        }
        assert consultar(["3_6", "mas_60", "sin_fecha"], "cero") == {"tres", "sin_fecha"}
        assert consultar([]) == consultar(None)
        assert consultar("sin_fecha") == {"sin_fecha"}
        assert consultar("3_6", "cero") == {"tres"}
        assert consultar("3_6", "con_saldo") == {"cuatro"}
        assert len(consultar(None)) == 14


def test_cumplir_un_mes_en_febrero_incluye_el_ultimo_dia_de_enero():
    _, menor_a_un_mes = _filtro_cuentas([2], "0_1", date(2026, 2, 28))
    _, de_uno_a_dos = _filtro_cuentas([2], "1_2", date(2026, 2, 28))
    assert menor_a_un_mes["fecha_desde_inclusiva"] == date(2026, 2, 1)
    assert de_uno_a_dos["fecha_hasta_exclusiva"] == date(2026, 2, 1)


def test_inactivacion_se_infiere_desde_el_estado_anterior_y_el_estado_actual():
    with connect(":memory:") as db:
        db.execute("ATTACH DATABASE ':memory:' AS AHORROS")
        db.execute("""
            CREATE TABLE AHORROS.CUENTA (NUMERO TEXT, CODIGOESTADO TEXT, IDAGENCIA INTEGER)
        """)
        db.executemany("INSERT INTO AHORROS.CUENTA VALUES (?, ?, 2)", [
            ("ultimo_cambio", "I"), ("reactivada_e_inactivada", "I"),
            ("cambios_con_misma_hora", "I"), ("solo_estado_anterior_i", "I"),
            ("sin_historico", "I"), ("actualmente_activa", "A"),
        ])
        db.execute("""
            CREATE TABLE AHORROS.CUENTAESTADO_HISTORICO (
                ID INTEGER PRIMARY KEY, NUMEROCUENTA TEXT, CODIGOESTADOCAMBIO TEXT,
                FECHA TEXT, FECHAPROCESO TEXT
            )
        """)
        db.executemany("INSERT INTO AHORROS.CUENTAESTADO_HISTORICO VALUES (?, ?, ?, ?, ?)", [
            # El último registro guarda A y el estado actual es I.
            (1, "ultimo_cambio", "A", "2026-10-23", "2026-10-24"),
            # A -> I, I -> A, A -> I y luego I -> I. Se conserva la segunda entrada.
            (2, "reactivada_e_inactivada", "A", "2020-01-01", "2020-01-02"),
            (3, "reactivada_e_inactivada", "I", "2026-01-01", "2026-01-02"),
            (4, "reactivada_e_inactivada", "A", "2026-08-23", "2026-08-24"),
            (5, "reactivada_e_inactivada", "I", "2026-09-01", "2026-09-02"),
            # El ID resuelve el orden cuando coinciden los tiempos de proceso.
            (6, "cambios_con_misma_hora", "A", "2020-01-01", "2020-01-02"),
            (7, "cambios_con_misma_hora", "I", "2026-03-01", "2026-03-02 01:00:00"),
            (8, "cambios_con_misma_hora", "A", "2026-03-01", "2026-03-02 01:00:00"),
            # Ver I como estado anterior no revela la fecha en que ingresó a I.
            (9, "solo_estado_anterior_i", "I", "2026-11-01", "2026-11-02"),
            (10, "actualmente_activa", "A", "2020-01-01", "2020-01-02"),
            (11, "actualmente_activa", "I", "2026-11-01", "2026-11-02"),
        ])
        historial = _HISTORIAL_INACTIVACION.replace("N'I'", "'I'").replace(
            "IN :ids_agencia", "= :id_agencia",
        )
        filas = db.execute(f"""
            WITH {historial}
            SELECT C.NUMERO, UI.FECHA
            FROM AHORROS.CUENTA AS C
            LEFT JOIN UltimaInactivacion AS UI ON UI.NUMEROCUENTA = C.NUMERO
            WHERE C.CODIGOESTADO = 'I'
        """, {"id_agencia": 2}).fetchall()
        assert len(filas) == 5
        assert dict(filas) == {
            "ultimo_cambio": "2026-10-23",
            "reactivada_e_inactivada": "2026-08-23",
            "cambios_con_misma_hora": "2026-03-01",
            "solo_estado_anterior_i": None,
            "sin_historico": None,
        }


def test_consolidado_requiere_agencias_en_resumen_y_detalle(cliente):
    client, fuente = cliente
    assert client.post(URL, json={"id_agencia": 0}).status_code == 422
    assert client.post(URL + "/detalle", json={"id_agencia": 0}).status_code == 422
    assert fuente.consultas == []


def test_endpoints_requieren_bearer():
    client = TestClient(app)
    assert client.post(URL, json={"id_agencia": 2}).status_code == 401
    assert client.post(URL + "/detalle", json={"id_agencia": 2}).status_code == 401
