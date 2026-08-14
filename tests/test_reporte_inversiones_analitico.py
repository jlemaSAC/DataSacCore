from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.inversiones.dependencies import get_reporte_inversiones_service
from app.modules.analytic.inversiones.repositories.sql_reporte_inversiones_repository import (
    _lista_desde_separador,
)
from app.modules.analytic.inversiones.service import ReporteInversionesService
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
        "periodicidad_pago": "MENSUAL",
        "tipo_pago": "PERIODICO",
        "condicion": "NUEVO",
        "periodo_plazo": "DE 31 A 90",
        "plazo_dias": 60,
        "estado": "ACTIVO",
        "provincia": "PICHINCHA",
        "canton": "QUITO",
        "parroquia": "CENTRO",
        "tiene_prestamo": False,
        "tasa_efectiva": 7.25,
        "tasa_entera": 7,
        "tasa_decimal": 7.25,
        "operaciones": 1,
        "saldo": saldo,
    }


class FakeMongoRepository:
    def __init__(self, filas: list[dict] | None = None) -> None:
        self.filas = filas or []
        self.indexes_ensured = False

    def ensure_indexes(self) -> None:
        self.indexes_ensured = True

    def obtener_periodos_cargados(self, periodos: list[str]) -> set[str]:
        return {fila["periodo"] for fila in self.filas if fila["periodo"] in periodos}

    def obtener_filas(self, periodos: list[str]) -> list[dict]:
        return [fila for fila in self.filas if fila["periodo"] in periodos]


class FakeSqlRepository:
    def __init__(self, filas: list[dict] | None = None) -> None:
        self.filas = filas or []
        self.fechas: list[date] = []

    def obtener_corte_actual(self, fecha_corte: date) -> list[dict]:
        self.fechas.append(fecha_corte)
        return self.filas


class FakeEtlClient:
    def __init__(self, mongo: FakeMongoRepository, *, genera: bool = True) -> None:
        self.mongo = mongo
        self.genera = genera
        self.fechas: list[date] = []

    def cargar_mes(self, fecha_fin_mes: date) -> dict:
        self.fechas.append(fecha_fin_mes)
        if self.genera:
            periodo = fecha_fin_mes.strftime("%Y-%m")
            self.mongo.filas.append(_fila(fecha_fin_mes.strftime("%Y%m%d"), periodo))
        return {}


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


def test_normaliza_tipos_y_productos_de_prestamo_como_listas() -> None:
    assert _lista_desde_separador("CREDI INVERSION SAC") == ["CREDI INVERSION SAC"]
    assert _lista_desde_separador("Producto A\u200bProducto B") == [
        "Producto A",
        "Producto B",
    ]
    assert _lista_desde_separador(None) == []


def test_genera_mes_cerrado_faltante_y_consulta_sql_para_hoy() -> None:
    mongo = FakeMongoRepository()
    sql = FakeSqlRepository([_fila("20260903", "2026-09", saldo=200.0)])
    etl = FakeEtlClient(mongo)
    service = ReporteInversionesService(mongo, sql, etl)  # type: ignore[arg-type]

    response = service.obtener_por_rango(date(2026, 8, 1), date(2026, 9, 3), _auth(date(2026, 9, 3)))

    assert mongo.indexes_ensured is True
    assert etl.fechas == [date(2026, 8, 31)]
    assert sql.fechas == [date(2026, 9, 3)]
    assert [(corte.periodo, corte.origen) for corte in response.cortes] == [
        ("2026-08", "ETL_EN_DEMANDA"),
        ("2026-09", "SQL_EN_LINEA"),
    ]
    assert response.total_operaciones == 2
    assert response.total_saldo == 300.0


def test_mes_sin_corte_intenta_etl_en_cada_consulta() -> None:
    mongo = FakeMongoRepository()
    sql = FakeSqlRepository()
    etl = FakeEtlClient(mongo, genera=False)
    service = ReporteInversionesService(mongo, sql, etl)  # type: ignore[arg-type]

    primera = service.obtener_por_rango(date(2019, 7, 1), date(2019, 7, 31), _auth(date(2026, 9, 3)))
    segunda = service.obtener_por_rango(date(2019, 7, 1), date(2019, 7, 31), _auth(date(2026, 9, 3)))

    assert etl.fechas == [date(2019, 7, 31), date(2019, 7, 31)]
    assert primera.cortes[0].origen == "SIN_CORTE_DISPONIBLE"
    assert segunda.cortes[0].origen == "SIN_CORTE_DISPONIBLE"


def test_endpoint_consulta_rango_autenticado() -> None:
    mongo = FakeMongoRepository([_fila("20260131", "2026-01")])
    service = ReporteInversionesService(mongo, FakeSqlRepository(), FakeEtlClient(mongo))  # type: ignore[arg-type]
    client = TestClient(app)
    app.dependency_overrides[get_reporte_inversiones_service] = lambda: service
    app.dependency_overrides[get_current_auth_context] = lambda: _auth(date(2026, 9, 3))
    try:
        response = client.get(
            "/analytic/depositos-a-plazos-historico",
            params={"fecha_desde": "2026-01-01", "fecha_hasta": "2026-01-31"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["cortes"][0]["origen"] == "MONGO"


def test_endpoint_rechaza_rango_invertido() -> None:
    client = TestClient(app)
    app.dependency_overrides[get_current_auth_context] = lambda: _auth(date(2026, 9, 3))
    try:
        response = client.get(
            "/analytic/depositos-a-plazos-historico",
            params={"fecha_desde": "2026-02-01", "fecha_hasta": "2026-01-31"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == "fecha_hasta no puede ser menor que fecha_desde."
