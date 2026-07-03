import logging
from datetime import date, datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.colocacion.colocacion_historico.dependencies import (
    get_colocacion_historico_service,
)
from app.modules.analytic.colocacion.colocacion_historico.repositories.mongo_colocacion_historico_repository import (
    CorteMensual,
    MongoColocacionHistoricoRepository,
)
from app.modules.analytic.colocacion.colocacion_historico.schemas import (
    InputSaldoInicialAgencia,
)
from app.modules.analytic.colocacion.colocacion_historico.service import (
    ColocacionHistoricoService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload


client = TestClient(app)


class FakeMongoCollection:
    def __init__(self) -> None:
        self.calls = 0
        self.pipeline = None
        self.hint = None

    def aggregate(self, pipeline: list[dict], hint: str) -> list[dict]:
        self.calls += 1
        self.pipeline = pipeline
        self.hint = hint
        return [
            {
                "_id": {"fecha_corte": "20260131", "agencia": "MATRIZ"},
                "saldo_inicial": 125.5,
            }
        ]


class FakeMongoDatabase:
    def __init__(self) -> None:
        self.collection = FakeMongoCollection()

    def __getitem__(self, name: str) -> FakeMongoCollection:
        assert name == "SituacionCrediticia"
        return self.collection


class FakeMongoRepository:
    def __init__(self, saldos: dict[int, dict[str, float]] | None = None) -> None:
        self.saldos = saldos or {}
        self.cortes = []
        self.calls = 0

    def obtener_saldos_iniciales_por_cortes(self, cortes: list) -> dict[int, dict[str, float]]:
        self.calls += 1
        self.cortes = cortes
        return {mes: dict(saldos) for mes, saldos in self.saldos.items()}


class FakeSqlRepository:
    def __init__(self, saldos: dict[str, float] | None = None) -> None:
        self.saldos = saldos or {}
        self.calls = 0

    def obtener_saldos_adjudicados_por_agencia(self, fecha_inicio, fecha_fin) -> dict[str, float]:
        self.calls += 1
        return dict(self.saldos)


class FailingMongoRepository:
    def obtener_saldos_iniciales_por_cortes(self, cortes: list) -> dict[int, dict[str, float]]:
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


def test_repositorio_mongo_agrega_todos_los_cortes_en_una_consulta() -> None:
    mongo_db = FakeMongoDatabase()
    repository = MongoColocacionHistoricoRepository(mongo_db)  # type: ignore[arg-type]

    saldos = repository.obtener_saldos_iniciales_por_cortes(
        [
            CorteMensual(
                mes=1,
                fecha_corte="20260131",
                fecha_inicio=datetime(2026, 1, 1),
                fecha_fin=datetime(2026, 1, 31, 23, 59, 59),
            ),
            CorteMensual(
                mes=2,
                fecha_corte="20260228",
                fecha_inicio=datetime(2026, 2, 1),
                fecha_fin=datetime(2026, 2, 28, 23, 59, 59),
            ),
        ]
    )

    assert mongo_db.collection.calls == 1
    assert mongo_db.collection.hint == "fecha_corte_1"
    assert len(mongo_db.collection.pipeline[0]["$match"]["$or"]) == 2
    assert saldos == {1: {"MATRIZ": 125.5}}


def test_servicio_consolida_mongo_y_sql_en_mes_actual() -> None:
    mongo_repository = FakeMongoRepository(
        {
            6: {"MATRIZ": 1000.0},
            7: {"MATRIZ": 200.0, "NORTE": 300.0},
        }
    )
    sql_repository = FakeSqlRepository({"MATRIZ": 50.0, "SUR": 75.0})
    service = ColocacionHistoricoService(mongo_repository, sql_repository)  # type: ignore[arg-type]

    response = service.obtener_saldo_inicial_agencias_por_mes(
        InputSaldoInicialAgencia(anio=2026),
        fake_auth_context(),
    )

    assert mongo_repository.calls == 1
    assert [corte.mes for corte in mongo_repository.cortes] == [1, 2, 3, 4, 5, 6, 7]
    assert mongo_repository.cortes[-1].fecha_corte == "20260702"
    assert sql_repository.calls == 1
    assert [item.agencia for item in response.agencias] == ["MATRIZ", "NORTE", "SUR"]
    matriz = response.agencias[0]
    assert len(matriz.meses) == 12
    assert matriz.meses[5].saldo_inicial == 1000.0
    assert matriz.meses[6].saldo_inicial == 250.0
    assert matriz.meses[11].saldo_inicial == 0.0


def test_primer_dia_del_mes_no_consulta_corte_mongo_del_mes_actual() -> None:
    mongo_repository = FakeMongoRepository()
    sql_repository = FakeSqlRepository({"MATRIZ": 10.0})
    service = ColocacionHistoricoService(mongo_repository, sql_repository)  # type: ignore[arg-type]

    response = service.obtener_saldo_inicial_agencias_por_mes(
        InputSaldoInicialAgencia(anio=2026),
        fake_auth_context(date(2026, 7, 1)),
    )

    assert [corte.mes for corte in mongo_repository.cortes] == [1, 2, 3, 4, 5, 6]
    assert response.agencias[0].meses[6].saldo_inicial == 10.0


def test_anio_futuro_no_genera_cortes_ni_consulta_sql() -> None:
    mongo_repository = FakeMongoRepository()
    sql_repository = FakeSqlRepository()
    service = ColocacionHistoricoService(mongo_repository, sql_repository)  # type: ignore[arg-type]

    response = service.obtener_saldo_inicial_agencias_por_mes(
        InputSaldoInicialAgencia(anio=2027),
        fake_auth_context(),
    )

    assert mongo_repository.cortes == []
    assert sql_repository.calls == 0
    assert response.agencias == []


def test_error_500_se_registra_en_consola_con_traceback(caplog) -> None:
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


def test_endpoint_devuelve_saldos() -> None:
    service = ColocacionHistoricoService(  # type: ignore[arg-type]
        FakeMongoRepository({6: {"MATRIZ": 500.0}}),
        FakeSqlRepository({"MATRIZ": 25.0}),
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
    assert response.json()["agencias"][0]["meses"][5]["saldo_inicial"] == 500.0
    assert response.json()["agencias"][0]["meses"][6]["saldo_inicial"] == 25.0
