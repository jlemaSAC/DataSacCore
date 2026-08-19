from datetime import date

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
from app.modules.analytic.ahorro_vista.dependencies import get_reporte_ahorro_vista_service
from app.modules.analytic.ahorro_vista.service import ReporteAhorroVistaService
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload


def _fila(fecha_corte: str, periodo: str, *, saldo: float = 100.0) -> dict:
    return {
        "fecha_corte": fecha_corte,
        "periodo": periodo,
        "anio": int(periodo[:4]),
        "mes": int(periodo[5:]),
        "agencia": "MATRIZ",
        "asesor": "ASESOR 1",
        "periodicidad": 60,
        "numero_transacciones_mes": 12,
        "numero_debitos_mes": 7,
        "numero_creditos_mes": 5,
        "tasa_entera": 2,
        "tasa_decimal": 2.5,
        "tiempo_inactivo_dias": 60,
        "estado": "ACTIVA",
        "provincia": "PICHINCHA",
        "canton": "QUITO",
        "parroquia": "CENTRO",
        "tiene_prestamo": True,
        "cantidad_prestamos": 2,
        "tipo_prestamo_lista": "MICROCREDITO\u200bCONSUMO",
        "producto_lista": "Producto A\u200bProducto B",
        "producto_ahorro": "AHORRO A LA VISTA",
        "es_programado": False,
        "saldo": saldo,
    }


class FakeSqlRepository:
    def __init__(self, filas: list[dict]) -> None:
        self.filas = filas
        self.rangos: list[tuple[date, date, bool | None]] = []

    def obtener_por_rango(
        self,
        fecha_desde: date,
        fecha_hasta: date,
        es_programado: bool | None = None,
    ) -> list[dict]:
        self.rangos.append((fecha_desde, fecha_hasta, es_programado))
        return self.filas


class FakeMongoRepository:
    def __init__(self, filas: list[dict] | None = None, *, corte_existe: bool | None = None) -> None:
        self.filas = filas or []
        self.corte_existe = filas is not None if corte_existe is None else corte_existe
        self.meses: list[tuple[date, bool | None]] = []
        self.cortes_verificados: list[date] = []

    def obtener_por_mes(self, mes: date, es_programado: bool | None = None) -> list[dict]:
        self.meses.append((mes, es_programado))
        return self.filas

    def existe_corte_mensual(self, mes: date) -> bool:
        self.cortes_verificados.append(mes)
        return self.corte_existe


class FakeEtlClient:
    def __init__(self) -> None:
        self.meses: list[tuple[date, date]] = []

    def cargar_mes(self, fecha_inicio: date, fecha_fin: date) -> dict:
        self.meses.append((fecha_inicio, fecha_fin))
        return {"total_cortes_procesados": 1}


def _auth(fecha_sistema: date) -> AuthContext:
    return AuthContext.from_token_payload(
        "token",
        UsuarioTokenPayload(
            sub="jdoe",
            usuario="John Doe",
            id_agencia=1,
            nombre_agencia="Matriz",
            fecha_sistema=fecha_sistema,
        ),
    )


def test_consulta_sql_directa_normaliza_dimensiones_y_listas() -> None:
    repository = FakeSqlRepository([_fila("20260818", "2026-08", saldo=200.0)])
    service = ReporteAhorroVistaService(repository, FakeMongoRepository(), FakeEtlClient())  # type: ignore[arg-type]

    response = service.obtener_por_rango(
        date(2026, 8, 1),
        date(2026, 8, 18),
        _auth(date(2026, 8, 18)),
    )

    assert repository.rangos == [(date(2026, 8, 18), date(2026, 8, 18), None)]
    assert response.total_transacciones_mes == 12
    assert response.filas[0].numero_debitos_mes == 7
    assert response.filas[0].numero_creditos_mes == 5
    assert response.total_saldo == 200.0
    assert response.cortes[0].fecha_corte == "20260818"
    assert response.filas[0].tipo_prestamo == ["MICROCREDITO", "CONSUMO"]
    assert response.filas[0].producto == ["Producto A", "Producto B"]


def test_endpoint_consulta_rango_autenticado_sin_etl() -> None:
    service = ReporteAhorroVistaService(
        FakeSqlRepository([_fila("20260818", "2026-08")]),
        FakeMongoRepository(),
        FakeEtlClient(),
    )  # type: ignore[arg-type]
    client = TestClient(app)
    app.dependency_overrides[get_reporte_ahorro_vista_service] = lambda: service
    app.dependency_overrides[get_current_auth_context] = lambda: _auth(date(2026, 8, 18))
    try:
        response = client.get(
            "/analytic/ahorros-vista-historico",
            params={"fecha_inicio": "2026-08-01", "fecha_fin": "2026-08-18"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["total_transacciones_mes"] == 12
    assert response.json()["filas"][0]["numero_transacciones_mes"] == 12
    assert response.json()["filas"][0]["numero_debitos_mes"] == 7
    assert response.json()["filas"][0]["numero_creditos_mes"] == 5


def test_rechaza_fecha_posterior_a_fecha_sistema() -> None:
    service = ReporteAhorroVistaService(
        FakeSqlRepository([]), FakeMongoRepository(), FakeEtlClient()
    )  # type: ignore[arg-type]

    with pytest.raises(HTTPException) as exc_info:
        service.obtener_por_rango(
            date(2026, 8, 1),
            date(2026, 8, 19),
            _auth(date(2026, 8, 18)),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "fecha_hasta no puede ser posterior a la fecha del sistema."


def test_mes_historico_cargado_se_consulta_desde_mongo() -> None:
    sql = FakeSqlRepository([])
    mongo = FakeMongoRepository([_fila("20260731", "2026-07", saldo=350.0)])
    etl = FakeEtlClient()
    service = ReporteAhorroVistaService(sql, mongo, etl)  # type: ignore[arg-type]

    response = service.obtener_por_rango(
        date(2026, 7, 1),
        date(2026, 7, 31),
        _auth(date(2026, 8, 18)),
        es_programado=False,
    )

    assert mongo.meses == [(date(2026, 7, 1), False)]
    assert sql.rangos == []
    assert etl.meses == []
    assert response.total_saldo == 350.0


def test_mes_historico_sin_carga_se_materializa_en_el_etl() -> None:
    sql = FakeSqlRepository([])
    mongo = FakeMongoRepository([_fila("20260731", "2026-07")], corte_existe=False)
    etl = FakeEtlClient()
    service = ReporteAhorroVistaService(sql, mongo, etl)  # type: ignore[arg-type]

    service.obtener_por_rango(
        date(2026, 7, 1),
        date(2026, 7, 31),
        _auth(date(2026, 8, 18)),
        es_programado=True,
    )

    assert mongo.meses == [(date(2026, 7, 1), True)]
    assert sql.rangos == []
    assert etl.meses == [(date(2026, 7, 1), date(2026, 7, 31))]
