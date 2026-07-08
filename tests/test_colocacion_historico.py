import logging
from datetime import date, datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.dialects import mssql

from app.main import app
from app.modules.analytic.colocacion.colocacion_historico.dependencies import (
    get_colocacion_historico_service,
)
from app.modules.analytic.colocacion.colocacion_historico.domain import (
    ColocacionAgrupada,
    DimensionesColocacion,
)
from app.modules.analytic.colocacion.colocacion_historico.repositories.mongo_colocacion_historico_repository import (
    CorteMensual,
    MongoColocacionHistoricoRepository,
)
from app.modules.analytic.colocacion.colocacion_historico.repositories.sql_colocacion_historico_repository import (
    SqlColocacionHistoricoRepository,
)
from app.modules.analytic.colocacion.colocacion_historico.schemas import (
    InputColocacionHistoricoRango,
    InputSaldoInicialAgencia,
)
from app.modules.analytic.colocacion.colocacion_historico.service import ColocacionHistoricoService
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload


client = TestClient(app)


def agrupacion(
    *,
    anio: int = 2026,
    mes: int,
    agencia: str = "MATRIZ",
    producto: str = "MICROCREDITO",
    operaciones: int = 1,
    saldo: float = 100.0,
) -> ColocacionAgrupada:
    return ColocacionAgrupada(
        dimensiones=DimensionesColocacion(
            periodo=f"{anio:04d}-{mes:02d}",
            anio=anio,
            mes=mes,
            agencia=agencia,
            condicion="NUEVO",
            tipo_prestamo="ORDINARIO",
            producto=producto,
            segmento="MINORISTA",
            asesor="JUAN PEREZ",
            provincia="AZUAY",
            canton="CUENCA",
            parroquia="EL VECINO",
            educacion="SUPERIOR",
            edad="HASTA 30",
            garantia="PERSONAL",
        ),
        operaciones=operaciones,
        saldo_inicial=saldo,
    )


class FakeMongoCollection:
    def __init__(self) -> None:
        self.calls = 0
        self.pipeline = None
        self.options = None

    def aggregate(self, pipeline: list[dict], **options) -> list[dict]:
        self.calls += 1
        self.pipeline = pipeline
        self.options = options
        return [
            {
                "_id": {
                    "fecha_corte": "20260131",
                    "agencia": "MATRIZ",
                    "condicion": "NUEVO",
                    "tipo_prestamo": "ORDINARIO",
                    "producto": "MICROCREDITO",
                    "segmento": "MINORISTA",
                    "asesor": "JUAN PEREZ",
                    "provincia": "AZUAY",
                    "canton": "CUENCA",
                    "parroquia": "EL VECINO",
                    "educacion": "SUPERIOR",
                    "edad": "HASTA 30",
                    "garantia": "PERSONAL",
                },
                "operaciones": 2,
                "saldo_inicial": 125.5,
            }
        ]


class FakeMongoDatabase:
    def __init__(self) -> None:
        self.collection = FakeMongoCollection()

    def __getitem__(self, name: str) -> FakeMongoCollection:
        assert name == "SituacionCrediticia"
        return self.collection


class FakeSqlSession:
    def __init__(self) -> None:
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return [
            (
                " matriz ",
                " nuevo ",
                " ordinario ",
                " microcredito ",
                " minorista ",
                " juan perez ",
                " azuay ",
                " cuenca ",
                " el vecino ",
                " superior ",
                datetime(1995, 8, 10),
                " personal ",
                2,
                125.0,
            )
        ]


class FakeMongoRepository:
    def __init__(self, datos: list[ColocacionAgrupada] | None = None) -> None:
        self.datos = datos or []
        self.cortes = []
        self.calls = 0

    def obtener_colocaciones_agrupadas(self, cortes: list) -> list[ColocacionAgrupada]:
        self.calls += 1
        self.cortes = cortes
        return list(self.datos)


class FakeSqlRepository:
    def __init__(self, datos: list[ColocacionAgrupada] | None = None) -> None:
        self.datos = datos or []
        self.calls = 0

    def obtener_colocaciones_agrupadas(self, fecha_inicio, fecha_fin) -> list[ColocacionAgrupada]:
        self.calls += 1
        return list(self.datos)


class FailingMongoRepository:
    def obtener_colocaciones_agrupadas(self, cortes: list) -> list[ColocacionAgrupada]:
        raise RuntimeError("Mongo no disponible")


def fake_auth_context(fecha_sistema: date = date(2026, 7, 3)) -> AuthContext:
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


def test_repositorio_mongo_agrupa_dimensiones_en_una_consulta() -> None:
    mongo_db = FakeMongoDatabase()
    repository = MongoColocacionHistoricoRepository(mongo_db)  # type: ignore[arg-type]

    datos = repository.obtener_colocaciones_agrupadas(
        [
            CorteMensual(
                anio=2026,
                mes=1,
                fecha_corte="20260131",
                fecha_inicio=datetime(2026, 1, 1),
                fecha_fin=datetime(2026, 1, 31, 23, 59, 59),
            )
        ]
    )

    assert mongo_db.collection.calls == 1
    assert mongo_db.collection.options == {"hint": "fecha_corte_1", "allowDiskUse": True}
    assert datos[0].dimensiones.producto == "MICROCREDITO"
    assert datos[0].dimensiones.garantia == "PERSONAL"
    assert datos[0].operaciones == 2
    assert datos[0].saldo_inicial == 125.5


def test_repositorio_sql_usa_exists_para_garantias_y_booleanos_validos() -> None:
    db = FakeSqlSession()
    repository = SqlColocacionHistoricoRepository(db)  # type: ignore[arg-type]

    datos = repository.obtener_colocaciones_agrupadas(
        datetime(2026, 7, 3),
        datetime(2026, 7, 3, 23, 59, 59),
    )
    sql = str(db.statement.compile(dialect=mssql.dialect(), compile_kwargs={"literal_binds": True}))

    assert "[ACTIVO] = 1" in sql
    assert "[ESPRINCIPAL] = 1" in sql
    assert "EXISTS" in sql
    assert " IS 1" not in sql
    assert datos[0].dimensiones.edad == "HASTA 30"
    assert datos[0].operaciones == 2


def test_servicio_consolida_mongo_sql_y_genera_resumen_dashboard() -> None:
    mongo_repository = FakeMongoRepository(
        [
            agrupacion(mes=6, operaciones=2, saldo=1000.0),
            agrupacion(mes=7, operaciones=1, saldo=200.0),
        ]
    )
    sql_repository = FakeSqlRepository(
        [agrupacion(mes=7, operaciones=1, saldo=50.0)]
    )
    service = ColocacionHistoricoService(mongo_repository, sql_repository)  # type: ignore[arg-type]

    response = service.obtener_saldo_inicial_agencias_por_mes(
        InputSaldoInicialAgencia(anio=2026),
        fake_auth_context(),
    )

    assert mongo_repository.calls == 1
    assert mongo_repository.cortes[-1].fecha_corte == "20260702"
    assert sql_repository.calls == 1
    assert response.total_operaciones == 4
    assert response.total_saldo_inicial == 1250.0
    assert response.resumen_mensual[5].saldo_inicial == 1000.0
    assert response.resumen_mensual[6].operaciones == 2
    assert response.resumen_mensual[6].saldo_inicial == 250.0
    assert len(response.agrupaciones) == 2


def test_anio_futuro_no_genera_datos() -> None:
    mongo_repository = FakeMongoRepository()
    sql_repository = FakeSqlRepository()
    service = ColocacionHistoricoService(mongo_repository, sql_repository)  # type: ignore[arg-type]

    response = service.obtener_saldo_inicial_agencias_por_mes(
        InputSaldoInicialAgencia(anio=2027),
        fake_auth_context(),
    )

    assert mongo_repository.cortes == []
    assert sql_repository.calls == 0
    assert response.agrupaciones == []
    assert len(response.resumen_mensual) == 12


def test_rango_se_segmenta_por_periodos_y_respeta_fechas_parciales() -> None:
    mongo_repository = FakeMongoRepository(
        [
            agrupacion(anio=2025, mes=12, operaciones=1, saldo=100.0),
            agrupacion(anio=2026, mes=1, operaciones=2, saldo=200.0),
            agrupacion(anio=2026, mes=2, operaciones=1, saldo=50.0),
        ]
    )
    sql_repository = FakeSqlRepository()
    service = ColocacionHistoricoService(mongo_repository, sql_repository)  # type: ignore[arg-type]

    response = service.obtener_colocacion_historica_por_rango(
        InputColocacionHistoricoRango(
            fecha_desde=date(2025, 12, 15),
            fecha_hasta=date(2026, 2, 10),
        ),
        fake_auth_context(),
    )

    assert [corte.fecha_corte for corte in mongo_repository.cortes] == [
        "20251231",
        "20260131",
        "20260210",
    ]
    assert mongo_repository.cortes[0].fecha_inicio == datetime(2025, 12, 15)
    assert sql_repository.calls == 0
    assert [item.periodo for item in response.resumen_mensual] == [
        "2025-12",
        "2026-01",
        "2026-02",
    ]
    assert response.resumen_mensual[0].fecha_desde == date(2025, 12, 15)
    assert response.resumen_mensual[-1].fecha_hasta == date(2026, 2, 10)
    assert response.total_operaciones == 4
    assert response.total_saldo_inicial == 350.0


def test_rango_actual_combina_mongo_hasta_ayer_y_sql_hoy() -> None:
    mongo_repository = FakeMongoRepository(
        [agrupacion(mes=7, operaciones=2, saldo=200.0)]
    )
    sql_repository = FakeSqlRepository(
        [agrupacion(mes=7, operaciones=1, saldo=75.0)]
    )
    service = ColocacionHistoricoService(mongo_repository, sql_repository)  # type: ignore[arg-type]

    response = service.obtener_colocacion_historica_por_rango(
        InputColocacionHistoricoRango(
            fecha_desde=date(2026, 7, 1),
            fecha_hasta=date(2026, 7, 3),
        ),
        fake_auth_context(),
    )

    assert mongo_repository.cortes[0].fecha_corte == "20260702"
    assert mongo_repository.cortes[0].fecha_fin.date() == date(2026, 7, 2)
    assert sql_repository.calls == 1
    assert response.total_operaciones == 3
    assert response.total_saldo_inicial == 275.0
    assert len(response.agrupaciones) == 1


def test_rango_rechaza_fecha_futura_y_mas_de_24_meses() -> None:
    service = ColocacionHistoricoService(  # type: ignore[arg-type]
        FakeMongoRepository(),
        FakeSqlRepository(),
    )

    with pytest.raises(HTTPException) as futura:
        service.obtener_colocacion_historica_por_rango(
            InputColocacionHistoricoRango(
                fecha_desde=date(2026, 7, 1),
                fecha_hasta=date(2026, 7, 4),
            ),
            fake_auth_context(),
        )
    assert futura.value.status_code == 400

    with pytest.raises(HTTPException) as extenso:
        service.obtener_colocacion_historica_por_rango(
            InputColocacionHistoricoRango(
                fecha_desde=date(2024, 1, 1),
                fecha_hasta=date(2026, 1, 1),
            ),
            fake_auth_context(),
        )
    assert extenso.value.status_code == 400


def test_error_500_se_registra_en_consola(caplog) -> None:
    service = ColocacionHistoricoService(  # type: ignore[arg-type]
        FailingMongoRepository(),
        FakeSqlRepository(),
    )

    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        with pytest.raises(HTTPException) as error:
            service.obtener_saldo_inicial_agencias_por_mes(
                InputSaldoInicialAgencia(anio=2026),
                fake_auth_context(),
            )

    assert error.value.status_code == 500
    assert "Error consultando colocacion historica para el anio 2026" in caplog.text
    assert "Mongo no disponible" in caplog.text


def test_endpoint_requiere_token() -> None:
    response = client.post(
        "/analytic/colocacion/colocacion-historico",
        json={"anio": 2026},
    )
    assert response.status_code == 401


def test_endpoint_devuelve_schema_para_dashboard() -> None:
    service = ColocacionHistoricoService(  # type: ignore[arg-type]
        FakeMongoRepository([agrupacion(mes=6, operaciones=2, saldo=500.0)]),
        FakeSqlRepository([agrupacion(mes=7, operaciones=1, saldo=25.0)]),
    )
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_colocacion_historico_service] = lambda: service
    try:
        response = client.post(
            "/analytic/colocacion/colocacion-historico",
            json={"anio": 2026},
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_colocacion_historico_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_operaciones"] == 3
    assert payload["total_saldo_inicial"] == 525.0
    assert payload["agrupaciones"][0]["producto"] == "MICROCREDITO"
    assert payload["agrupaciones"][0]["garantia"] == "PERSONAL"


def test_endpoint_rango_devuelve_periodos_mensuales() -> None:
    service = ColocacionHistoricoService(  # type: ignore[arg-type]
        FakeMongoRepository([agrupacion(mes=6, operaciones=2, saldo=500.0)]),
        FakeSqlRepository(),
    )
    app.dependency_overrides[get_current_auth_context] = fake_auth_context
    app.dependency_overrides[get_colocacion_historico_service] = lambda: service
    try:
        response = client.post(
            "/analytic/colocacion/colocacion-historico/rango",
            json={"fecha_desde": "2026-06-15", "fecha_hasta": "2026-06-30"},
        )
    finally:
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_colocacion_historico_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["fecha_desde"] == "2026-06-15"
    assert payload["resumen_mensual"][0]["periodo"] == "2026-06"
    assert payload["agrupaciones"][0]["anio"] == 2026
