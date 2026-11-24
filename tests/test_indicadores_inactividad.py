from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects.mssql import pyodbc

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.cuentas.indicadores_inactividad.dependencies import get_indicadores_inactividad_service
from app.modules.negocios.cuentas.indicadores_inactividad.repositories.sql_indicadores_inactividad_repository import (
    SqlIndicadoresInactividadRepository,
)
from app.modules.negocios.cuentas.indicadores_inactividad.service import IndicadoresInactividadService


URL = "/negocios/cuentas/indicadores-de-inactividad"
HOY = date(2026, 11, 24)

TOTAL = dict(
    dimension="total", cuentas_brutas=5, cuentas_positivas=2, cuentas_cero=2,
    saldo_total=Decimal("100.000001"), saldo_maximo=Decimal("100.000000"),
    saldo_minimo=Decimal("0.000001"), cuentas_con_dias=2, dias_promedio=Decimal("20"),
    dias_maximo=30, dias_minimo=10, cuentas_con_inactivacion=1,
    inactivacion_promedio=Decimal("7"), inactivacion_maximo=7, inactivacion_minimo=7,
)


def _fila(dimension, **valores):
    return dict(
        dict(
            dimension=dimension, rango_edad=None, sexo=None, estado_civil=None, socio=None,
            id_agencia=None, agencia=None, anio=None, mes=None, cuentas_positivas=1,
        ),
        **valores,
    )


@pytest.fixture
def cliente():
    class Repositorio:
        def __init__(self):
            self.consultas = []

        def obtener_indicadores(self, **kwargs):
            self.consultas.append(kwargs)
            if kwargs["ids_agencia"] == [9]:
                return [dict(
                    TOTAL, cuentas_brutas=0, cuentas_positivas=0, cuentas_cero=0,
                    saldo_total=Decimal("0"), saldo_maximo=None, saldo_minimo=None,
                    cuentas_con_dias=0, dias_promedio=None, dias_maximo=None, dias_minimo=None,
                    cuentas_con_inactivacion=0, inactivacion_promedio=None,
                    inactivacion_maximo=None, inactivacion_minimo=None,
                )]
            if kwargs["ids_agencia"] == [17]:
                return [
                    _fila("socio", socio="Socio", saldo_total=Decimal("100.000001")),
                    _fila("socio", socio="No socio", saldo_total=Decimal("50.000003")),
                    _fila("socio", saldo_total=Decimal("0.000001")),
                    dict(
                        TOTAL, cuentas_brutas=3, cuentas_positivas=3, cuentas_cero=0,
                        saldo_total=Decimal("150.000005"), saldo_maximo=Decimal("100.000001"),
                        saldo_minimo=Decimal("0.000001"),
                    ),
                ]
            return [
                _fila("rango_edad", rango_edad=18), _fila("rango_edad", rango_edad=0),
                _fila("sexo", sexo="Mujer"), _fila("sexo"),
                _fila("estado_civil", estado_civil="SOLTERO"), _fila("estado_civil"),
                _fila("socio", socio="Socio", saldo_total=Decimal("100.000000")),
                _fila("socio", socio="No socio", saldo_total=Decimal("0.000001")),
                _fila("agencia", id_agencia=2, agencia="Agencia de prueba", cuentas_positivas=2),
                _fila("anio", anio=2026, cuentas_positivas=2),
                _fila("mes_agencia", mes="2026-10", id_agencia=2, agencia="Agencia de prueba"),
                _fila("mes_agencia", mes="2026-09", id_agencia=2, agencia="Agencia de prueba"),
                _fila("mes_apertura", mes_apertura="2021-11"),
                _fila("mes_apertura", mes_apertura="2022-11"),
                TOTAL,
            ]

    repo = Repositorio()
    auth = AuthContext.from_token_payload("token", UsuarioTokenPayload(
        sub="test", usuario="prueba", id_agencia=2, fecha_sistema=HOY,
    ))
    app.dependency_overrides[get_current_auth_context] = lambda: auth
    app.dependency_overrides[get_indicadores_inactividad_service] = lambda: IndicadoresInactividadService(repo)
    try:
        yield TestClient(app), repo
    finally:
        app.dependency_overrides.pop(get_current_auth_context)
        app.dependency_overrides.pop(get_indicadores_inactividad_service)


def test_corte_de_sistema_y_distribuciones_sobre_cuentas_positivas(cliente):
    client, repo = cliente
    respuesta = client.post(URL, json={"id_agencia": 2})

    assert respuesta.status_code == 200
    assert repo.consultas == [dict(ids_agencia=[2], fecha_sistema=HOY, incluir_analisis=True)]
    data = respuesta.json()
    assert data["fecha_corte"] == HOY.isoformat()
    assert data["generales"] == dict(
        cuentas_brutas=5, cuentas_cero=2, cuentas_positivas=2, cuentas_seleccionadas=5,
        porcentaje_base_bruta=100, porcentaje_con_saldo=40,
        saldo_total="100.000001",
        saldo_socios="100.000000", saldo_no_socios="0.000001", saldo_socio_no_especificado="0",
        saldo_maximo="100.000000", saldo_minimo="0.000001", saldo_restante="0",
    )
    assert data["inactividad"] == dict(cuentas_con_dato=1, promedio=7, maximo=7, minimo=7, rango=0)
    assert data["ultima_transaccion_activa"] == dict(
        cuentas_con_dato=2, promedio=20, maximo=30, minimo=10, rango=20,
    )
    assert "edad" not in data
    dimensiones = data["dimensiones"]
    assert len(dimensiones["rango_edad"]) == 8
    assert dimensiones["rango_edad"][0]["nombre"] == "No especificado"
    assert dimensiones["rango_edad"][0]["cantidad"] == 1
    for grupos in dimensiones.values():
        assert sum(fila["cantidad"] for fila in grupos) == 2
        assert sum(fila["porcentaje"] for fila in grupos) == 100
    assert [fila["clave"] for fila in dimensiones["mes_agencia"]] == ["2026-10:2", "2026-09:2"]
    assert [fila["clave"] for fila in dimensiones["mes_apertura"]] == ["2022-11", "2021-11"]


@pytest.mark.parametrize("condicion_saldo,incluir_analisis", [("cero", False), ("positivo", True)])
def test_filtra_consolidado_actual_y_conserva_la_base_bruta(cliente, condicion_saldo, incluir_analisis):
    client, repo = cliente
    respuesta = client.post(URL, json={
        "id_agencia": 0, "ids_agencia": [17, 2, 17],
        "condicion_saldo": condicion_saldo,
    })
    assert respuesta.status_code == 200
    assert repo.consultas == [dict(
        ids_agencia=[2, 17], fecha_sistema=HOY, incluir_analisis=incluir_analisis,
    )]
    data = respuesta.json()
    assert data["fecha_corte"] == HOY.isoformat()
    assert data["generales"]["cuentas_brutas"] == 5
    assert data["generales"]["cuentas_seleccionadas"] == 2
    assert Decimal(data["generales"]["saldo_socios"]) == (Decimal("100") if incluir_analisis else 0)
    assert Decimal(data["generales"]["saldo_no_socios"]) == (Decimal("0.000001") if incluir_analisis else 0)
    assert bool(data["inactividad"]) is incluir_analisis
    assert bool(data["ultima_transaccion_activa"]) is incluir_analisis
    assert all(bool(filas) is incluir_analisis for filas in data["dimensiones"].values())


def test_fecha_en_un_cuerpo_antiguo_no_reemplaza_la_fecha_de_sistema(cliente):
    client, repo = cliente
    respuesta = client.post(URL, json={"id_agencia": 2, "fecha_corte": "2026-10-31"})
    assert respuesta.status_code == 200
    assert respuesta.json()["fecha_corte"] == HOY.isoformat()
    assert repo.consultas == [dict(ids_agencia=[2], fecha_sistema=HOY, incluir_analisis=True)]


def test_validacion_de_filtros(cliente):
    client, repo = cliente
    assert client.post(URL, json={"id_agencia": 0}).status_code == 422
    assert client.post(URL, json={"id_agencia": 2, "condicion_saldo": "negativo"}).status_code == 422
    assert repo.consultas == []


def test_saldos_por_socio_incluyen_los_no_especificados_sin_redondear(cliente):
    client, _ = cliente
    respuesta = client.post(URL, json={"id_agencia": 17, "condicion_saldo": "positivo"})
    assert respuesta.status_code == 200
    generales = respuesta.json()["generales"]
    assert generales["saldo_restante"] == "50.000003"
    assert generales["saldo_socio_no_especificado"] == "0.000001"
    assert sum(
        Decimal(generales[clave])
        for clave in ("saldo_socios", "saldo_no_socios", "saldo_socio_no_especificado")
    ) == Decimal(generales["saldo_total"])


def test_indicadores_sin_base(cliente):
    client, _ = cliente
    respuesta = client.post(URL, json={"id_agencia": 9})
    assert respuesta.status_code == 200
    data = respuesta.json()
    assert data["generales"]["cuentas_brutas"] == 0
    assert data["generales"]["porcentaje_base_bruta"] is None
    assert data["generales"]["porcentaje_con_saldo"] is None
    assert data["inactividad"]["rango"] is None
    assert data["ultima_transaccion_activa"]["promedio"] is None
    assert not any(data["dimensiones"].values())


@pytest.mark.parametrize("incluir_analisis", [True, False])
def test_repositorio_compila_un_solo_agregado_a_fecha_de_sistema(incluir_analisis):
    class Sesion:
        def execute(self, consulta, parametros):
            compilada = consulta.params(**parametros).compile(
                dialect=pyodbc.dialect(paramstyle="qmark"),
                compile_kwargs={"render_postcompile": True},
            )
            self.sql = str(compilada)
            self.params = compilada.params
            return self

        def mappings(self):
            return self

        def all(self):
            return []

    db = Sesion()
    repo = SqlIndicadoresInactividadRepository(db)
    repo.obtener_indicadores(
        ids_agencia=[2, 17], fecha_sistema=HOY, incluir_analisis=incluir_analisis,
    )
    assert "GROUP BY GROUPING SETS" in db.sql
    assert "(mes, id_agencia, agencia), (mes_apertura)" in db.sql
    assert "CONVERT(char(7), C.FECHACREACION, 126)" in db.sql
    assert "WHEN GROUPING(mes_apertura) = 0 THEN 'mes_apertura'" in db.sql
    assert db.sql.count("SUM(CI.SALDO)") == 1
    assert "ROUND(" not in db.sql
    if incluir_analisis:
        assert "FROM AHORROS.CUENTAESTADO_HISTORICO AS H" in db.sql
        assert "INNER JOIN CuentasCandidatas AS ACTUAL" in db.sql
        assert "estado_anterior <> N'I' AND estado_resultante = N'I'" in db.sql
        assert "DATEDIFF(day, UI.FECHA, ?) AS dias_inactivacion" in db.sql
        assert "LEFT JOIN UltimaInactivacion AS UI ON UI.NUMEROCUENTA = B.NUMERO AND B.saldo > 0" in db.sql
    else:
        assert "CUENTAESTADO_HISTORICO" not in db.sql
        assert "CAST(NULL AS int) AS dias_inactivacion" in db.sql
    assert "DATEDIFF(day, B.ultima_transaccion, ?)" in db.sql
    assert "FECHAULTIMATRANSACCIONACTIVA" in db.sql
    assert "C.IDAGENCIA IN (?, ?)" in db.sql
    assert db.params["ids_agencia_1"] == 2
    assert db.params["fecha_sistema"] == HOY
    assert "FOR SYSTEM_TIME" not in db.sql
    assert "FECHANACIMIENTO" in db.sql and "DATEADD(year, N.anios, N.nacimiento)" in db.sql
    assert "ORDER BY CC.IDCLIENTE, CC.ID" in db.sql
