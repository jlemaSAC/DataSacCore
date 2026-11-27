from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.mssql import pyodbc

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.cuentas.control_cuentas_activas.dependencies import (
    get_control_cuentas_activas_service,
)
from app.modules.negocios.cuentas.control_cuentas_activas.repositories.sql_control_cuentas_activas_repository import (
    _AGRUPADOS,
    SqlControlCuentasActivasRepository,
)
from app.modules.negocios.cuentas.control_cuentas_activas.service import ControlCuentasActivasService
from app.modules.negocios.cuentas.sql_cuentas import AGENCIA_EXPANDIBLE


URL = "/negocios/cuentas/control-de-cuentas-activas"
FILTROS = {"fecha_inicio": "2026-11-01", "fecha_fin": "2026-11-24", "id_agencia": 2}


@pytest.fixture
def cliente(monkeypatch):
    class Fuente:
        def get_oficinas_consulta(self, codigo):
            assert codigo == "PRUEBA"
            return [SimpleNamespace(id=2), SimpleNamespace(id=17)]

        def obtener_resumen(self, agencias, inicio, fin):
            assert (agencias, inicio, fin) == ([2, 17], date(2026, 11, 1), date(2026, 11, 24))
            return [
                {
                    "id_agencia": id_agencia, "agencia": f"Agencia {id_agencia}",
                    "codigo_tipo_cuenta": "002", "tipo_cuenta": "Vista",
                    "codigo_asesor": asesor, "asesor": asesor, "cargo": "CAPTADOR",
                    "cantidad_cuentas": 1, "cantidad_reactivaciones": cantidad,
                }
                for id_agencia, asesor, cantidad in [(2, "ANA", 2), (2, "BEA", 1), (17, "LUIS", 1)]
            ]

        def obtener_gerentes_oficina(self, agencias):
            assert agencias == {"Agencia 2", "Agencia 17"}
            return [{"IdAgencia": 2, "Cargo": "JEFE DE AGENCIA", "GerenteOficina": "María"}]

        def obtener_detalle(self, agencias, inicio, fin, *, cargos, asesores, desplazamiento, tamano_pagina,
                            codigo_tipo_cuenta):
            assert (agencias, inicio, fin) == ([2], date(2026, 11, 1), date(2026, 11, 24))
            assert (desplazamiento, tamano_pagina) == (25, 25)
            assert (cargos, asesores) == (["CAPTADOR"], ["ANA"])
            assert codigo_tipo_cuenta == "002"
            return [{
                "id_reactivacion": 3, "fecha_reactivacion": date(2026, 11, 12),
                "numero_cuenta": "001", "titular": None, "tipo_cuenta": "Vista", "agencia": "Matriz",
                "cargo": "CAPTADOR", "asesor": "ANA",
            }]

    fuente = Fuente()
    auth = AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="PRUEBA", usuario="Usuario de prueba", id_agencia=2,
        fecha_sistema=datetime(2026, 11, 24, 13, 0),
    ))
    monkeypatch.setitem(app.dependency_overrides, get_current_auth_context, lambda: auth)
    monkeypatch.setitem(app.dependency_overrides, get_control_cuentas_activas_service,
                        lambda: ControlCuentasActivasService(fuente, fuente, fuente))
    return TestClient(app)


def test_endpoints_devuelven_resumen_consolidado_y_detalle_paginado(cliente):
    resumen = cliente.post(URL, json={**FILTROS, "id_agencia": 0, "ids_agencia": [17, 2, 17]})
    assert resumen.status_code == 200
    assert resumen.json()["total"] == {"cantidad_cuentas": 3, "cantidad_reactivaciones": 4}
    assert [fila["id_agencia"] for fila in resumen.json()["resumen"]] == [2, 17]
    assert resumen.json()["resumen"][0]["cantidad_cuentas"] == 2
    assert resumen.json()["resumen"][0]["cargo_jefe_agencia"] == "JEFE DE AGENCIA"
    assert resumen.json()["resumen"][0]["nombre_jefe_agencia"] == "María"
    assert resumen.json()["resumen"][1]["nombre_jefe_agencia"] is None
    assert [fila["codigo_asesor"] for fila in resumen.json()["desglose"]] == ["ANA", "BEA", "LUIS"]

    detalle = cliente.post(URL + "/detalle", json={
        **FILTROS, "desplazamiento": 25, "cargos": ["CAPTADOR"], "asesores": ["ANA"],
        "codigo_tipo_cuenta": "002",
    })
    assert detalle.status_code == 200
    assert detalle.json()["filas"][0]["fecha_reactivacion"] == "2026-11-12"
    assert detalle.json()["filas"][0]["id_reactivacion"] == 3
    assert detalle.json()["filas"][0]["asesor"] == "ANA"


@pytest.mark.parametrize(("cambios", "estado"), [
    ({"fecha_inicio": "2026-10-31"}, 422),
    ({"fecha_inicio": "2026-11-25"}, 422),
    ({"fecha_fin": "2026-11-25"}, 400),
    ({"id_agencia": 99}, 403),
    ({"id_agencia": 0, "ids_agencia": [2, 99]}, 403),
    ({"id_agencia": 0}, 422),
])
@pytest.mark.parametrize("sufijo", ["", "/detalle"])
def test_valida_fechas_y_agencias_en_ambos_endpoints(cliente, cambios, estado, sufijo):
    assert cliente.post(URL + sufijo, json={**FILTROS, **cambios}).status_code == estado


@pytest.mark.parametrize("sufijo", ["", "/detalle"])
def test_exige_bearer(monkeypatch, sufijo):
    def servicio():
        raise AssertionError("La consulta sin token no debe construir el servicio.")

    monkeypatch.setitem(app.dependency_overrides, get_control_cuentas_activas_service, servicio)
    assert TestClient(app).post(URL + sufijo, json=FILTROS).status_code == 401


def test_resumen_identifica_transiciones_y_cuentas_unicas_con_el_historial_completo():
    engine = create_engine("sqlite://")
    with engine.begin() as db:
        db.exec_driver_sql("ATTACH DATABASE ':memory:' AS AHORROS")
        db.exec_driver_sql("""
            CREATE TABLE AHORROS.CUENTA (
                NUMERO TEXT, IDAGENCIA INTEGER, CODIGOTIPOCUENTA TEXT, CODIGOESTADO TEXT,
                CODIGOUSUARIOOFICIAL TEXT DEFAULT 'ASESOR'
            )
        """)
        db.exec_driver_sql("""
            CREATE TABLE AHORROS.CUENTAESTADO_HISTORICO (
                ID INTEGER, NUMEROCUENTA TEXT, CODIGOESTADOCAMBIO TEXT, FECHA TEXT, FECHAPROCESO TEXT
            )
        """)
        db.exec_driver_sql("""
            INSERT INTO AHORROS.CUENTA (NUMERO, IDAGENCIA, CODIGOTIPOCUENTA, CODIGOESTADO)
            VALUES (?, ?, ?, ?)
        """, [
            ("reincidente", 2, "V", "I"), ("activa_actual", 2, "V", "A"),
            ("siguiente_mes", 2, "P", "I"), ("bloqueada", 2, "V", "B"),
            ("otra_agencia", 17, "V", "A"), ("sin_historial", 2, "V", "A"),
            ("fuera_rango", 2, "V", "A"),
        ])
        db.exec_driver_sql("INSERT INTO AHORROS.CUENTAESTADO_HISTORICO VALUES (?, ?, ?, ?, ?)", [
            (1, "reincidente", "I", "2026-11-01 00:00:00", "2026-11-01 12:00:00"),
            (2, "reincidente", "A", "2026-11-02 00:00:00", "2026-11-02 12:00:00"),
            (3, "reincidente", "I", "2026-11-05 00:00:00", "2026-11-05 12:00:00"),
            (4, "reincidente", "A", "2026-11-05 00:00:00", "2026-11-05 12:00:00"),
            (5, "activa_actual", "I", "2026-11-24 23:59:59", "2026-11-25 12:00:00"),
            (6, "siguiente_mes", "I", "2026-11-03 00:00:00", "2026-11-03 12:00:00"),
            (7, "siguiente_mes", "A", "2026-12-01 00:00:00", "2026-12-01 12:00:00"),
            (8, "bloqueada", "I", "2026-11-08 00:00:00", "2026-11-08 12:00:00"),
            (9, "otra_agencia", "I", "2026-11-03 00:00:00", "2026-11-03 12:00:00"),
            (10, "fuera_rango", "I", "2026-11-25 00:00:00", "2026-11-25 12:00:00"),
        ])

        resumen = text(
            _AGRUPADOS.replace("N'", "'").replace("COUNT_BIG", "COUNT")
            + "SELECT * FROM Agrupados ORDER BY CODIGOTIPOCUENTA"
        ).bindparams(AGENCIA_EXPANDIBLE)
        filas = db.execute(resumen, {
            "ids_agencia": [2], "fecha_inicio": "2026-11-01", "fecha_hasta_exclusiva": "2026-11-25",
        }).mappings().all()

    assert [(f["CODIGOTIPOCUENTA"], f["cantidad_cuentas"], f["cantidad_reactivaciones"])
            for f in filas] == [("P", 1, 1), ("V", 2, 3)]


def test_detalle_compila_filtros_de_personal_antes_de_ordenar_y_paginar():
    class Sesion:
        def execute(self, consulta, parametros):
            self.compilada = consulta.params(**parametros).compile(
                dialect=pyodbc.dialect(), compile_kwargs={"render_postcompile": True},
            )
            return self

        def mappings(self):
            return self

        def all(self):
            return []

    db = Sesion()
    SqlControlCuentasActivasRepository(db).obtener_detalle(
        [2, 17], date(2026, 11, 1), date(2026, 11, 24),
        cargos=["CAPTADOR"], asesores=["ANA"], desplazamiento=25, tamano_pagina=25,
        codigo_tipo_cuenta="002",
    )
    assert db.compilada.params["ids_agencia_1"] == 2
    assert db.compilada.params["ids_agencia_2"] == 17
    assert db.compilada.params["cargos_1"] == "CAPTADOR"
    assert db.compilada.params["asesores_1"] == "ANA"
    assert db.compilada.params["codigo_tipo_cuenta"] == "002"
    sql = str(db.compilada)
    assert sql.index("C.CODIGOUSUARIOOFICIAL IN (:asesores_1)") < sql.index("Cambios AS")
    assert sql.index("C.CODIGOTIPOCUENTA = :codigo_tipo_cuenta") < sql.index("Cambios AS")
    assert "ORDER BY R.FECHA DESC, R.ID DESC" in sql
    assert "OFFSET :desplazamiento ROWS FETCH NEXT :tamano_pagina ROWS ONLY" in sql
