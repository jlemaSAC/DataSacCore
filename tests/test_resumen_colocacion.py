from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.dialects import mssql

from app.main import app
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.colocacion.resumen.dependencies import get_resumen_colocacion_service
from app.modules.negocios.colocacion.resumen.repositories.sql_colocacion_resumen_repository import (
    PeriodosComparacionColocacion,
    SqlColocacionResumenRepository,
    TotalesColocacion,
)
from app.modules.negocios.colocacion.resumen.schemas import InputResumenColocacion
from app.modules.negocios.colocacion.resumen.service import ResumenColocacionService


client = TestClient(app)


def auth_context(fecha_sistema: date = date(2026, 8, 31)) -> AuthContext:
    return AuthContext.from_token_payload(
        "token",
        UsuarioTokenPayload(
            sub="jdoe",
            usuario="John Doe",
            id_agencia=2,
            nombre_agencia="Matriz",
            fecha_sistema=fecha_sistema,
        ),
    )


class FakeRepository:
    def __init__(self) -> None:
        self.agencias = []
        self.dimensiones = []
        self.periodos = None

    def obtener_por_agencia(self, agencia_ids, periodos):
        self.agencias = agencia_ids
        self.periodos = periodos
        return [
            TotalesColocacion(
                id_agencia=2,
                agencia="MATRIZ",
                dimension=None,
                monto_colocado=100.0,
                monto_colocado_periodo_anterior=80.0,
                monto_mes_a_fecha=100.0,
                monto_mes_anterior_mismo_dia=0.0,
            )
        ]

    def obtener_por_dimension(self, agencia_ids, periodos, dimension):
        self.dimensiones.append(dimension)
        return [
            TotalesColocacion(
                id_agencia=2,
                agencia="MATRIZ",
                dimension="MICROCREDITO",
                monto_colocado=50.0,
                monto_colocado_periodo_anterior=100.0,
                monto_mes_a_fecha=50.0,
                monto_mes_anterior_mismo_dia=25.0,
            )
        ]


class EmptyResult:
    def mappings(self):
        return []


class FakeSession:
    def __init__(self) -> None:
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return EmptyResult()


def test_servicio_calcula_periodos_comparativos_y_variaciones() -> None:
    repository = FakeRepository()
    service = ResumenColocacionService(repository)  # type: ignore[arg-type]

    respuesta = service.obtener_resumen(
        InputResumenColocacion(
            agencia_ids=[2, 2],
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 8, 31),
        ),
        auth_context(),
    )

    assert repository.agencias == [2]
    assert repository.dimensiones == [
        "tipo_prestamo",
        "producto",
        "segmento",
        "condicion",
    ]
    assert repository.periodos == PeriodosComparacionColocacion(
        actual_inicio=date(2026, 8, 1),
        actual_fin=date(2026, 8, 31),
        anterior_inicio=date(2026, 7, 1),
        anterior_fin=date(2026, 7, 31),
        mes_a_fecha_inicio=date(2026, 8, 1),
        mes_a_fecha_fin=date(2026, 8, 31),
        mes_anterior_inicio=date(2026, 7, 1),
        mes_anterior_fin=date(2026, 7, 31),
    )
    assert respuesta.resumen_por_agencia[0].variacion_valor == 20.0
    assert respuesta.resumen_por_agencia[0].variacion_porcentaje == 25.0
    assert respuesta.resumen_por_agencia[0].variacion_mes_a_fecha_porcentaje is None
    assert respuesta.por_producto[0].variacion_porcentaje == -50.0
    assert respuesta.por_producto[0].variacion_mes_a_fecha_porcentaje == 100.0


def test_servicio_rechaza_fecha_final_posterior_a_fecha_del_sistema() -> None:
    service = ResumenColocacionService(FakeRepository())  # type: ignore[arg-type]

    with pytest.raises(HTTPException, match="fecha_fin no puede ser posterior") as error:
        service.obtener_resumen(
            InputResumenColocacion(
                agencia_ids=[2],
                fecha_inicio=date(2026, 8, 1),
                fecha_fin=date(2026, 9, 1),
            ),
            auth_context(),
        )

    assert error.value.status_code == 400


def test_servicio_usa_mes_anterior_cerrado_y_mismo_dia_para_el_mtd() -> None:
    repository = FakeRepository()
    service = ResumenColocacionService(repository)  # type: ignore[arg-type]

    service.obtener_resumen(
        InputResumenColocacion(
            agencia_ids=[2],
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 8, 25),
        ),
        auth_context(),
    )

    assert repository.periodos == PeriodosComparacionColocacion(
        actual_inicio=date(2026, 8, 1),
        actual_fin=date(2026, 8, 25),
        anterior_inicio=date(2026, 7, 1),
        anterior_fin=date(2026, 7, 31),
        mes_a_fecha_inicio=date(2026, 8, 1),
        mes_a_fecha_fin=date(2026, 8, 25),
        mes_anterior_inicio=date(2026, 7, 1),
        mes_anterior_fin=date(2026, 7, 25),
    )


def test_repositorio_construye_consulta_parametrizada_con_las_dimensiones() -> None:
    db = FakeSession()
    repository = SqlColocacionResumenRepository(db)  # type: ignore[arg-type]
    periodos = PeriodosComparacionColocacion(
        actual_inicio=date(2026, 8, 1),
        actual_fin=date(2026, 8, 31),
        anterior_inicio=date(2026, 7, 1),
        anterior_fin=date(2026, 7, 31),
        mes_a_fecha_inicio=date(2026, 8, 1),
        mes_a_fecha_fin=date(2026, 8, 31),
        mes_anterior_inicio=date(2026, 7, 1),
        mes_anterior_fin=date(2026, 7, 31),
    )

    repository.obtener_por_dimension([2, 17], periodos, "producto")

    sql = str(db.statement.compile(dialect=mssql.dialect()))
    assert "[COLOCACION].[PRESTAMO]" in sql
    assert "[GENERAL].[AGENCIA]" in sql
    assert "[CREDITO].[CALIFICACION_CONTABLE]" in sql
    assert "[PRESTAMO].[IDAGENCIA] IN" in sql
    assert "[PRESTAMO].[FECHAADJUDICACION]" in sql
    assert "GROUP BY" in sql


def test_endpoint_devuelve_los_cinco_desgloses() -> None:
    service = ResumenColocacionService(FakeRepository())  # type: ignore[arg-type]
    app.dependency_overrides[get_current_auth_context] = auth_context
    app.dependency_overrides[get_resumen_colocacion_service] = lambda: service
    try:
        response = client.post(
            "/negocios/colocacion/resumen",
            json={
                "agencia_ids": [2],
                "fecha_inicio": "2026-08-01",
                "fecha_fin": "2026-08-31",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["resumen_por_agencia"][0]["dimension"] is None
    assert len(body["por_tipo_prestamo"]) == 1
    assert len(body["por_producto"]) == 1
    assert len(body["por_segmento"]) == 1
    assert len(body["por_condicion"]) == 1
