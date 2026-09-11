from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.recuperacion.recuperacion_historico.domain import (
    RecuperacionResumenAgrupada,
    ResultadoResumenRecuperacion,
)
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.mongo_recuperacion_historico_repository import (
    MongoRecuperacionHistoricoRepository,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.recuperacion.resumen.dependencies import (
    get_resumen_recuperacion_service,
)
from app.modules.negocios.recuperacion.resumen.schemas import InputResumenRecuperacion
from app.modules.negocios.recuperacion.resumen.service import ResumenRecuperacionService


client = TestClient(app)
DIMENSIONES = (
    "agencia",
    "asesor",
    "cargo",
    "tipo_prestamo",
    "producto",
    "condicion",
    "tipo_cobro",
    "abogado",
)


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


class FakeRecuperacionHistoricoService:
    def __init__(self) -> None:
        self.llamadas: list[tuple] = []

    def obtener_agrupaciones_resumen_por_rango(
        self,
        fecha_inicio,
        fecha_fin,
        fecha_hoy,
        agencias,
        asesores,
        cargos,
    ) -> ResultadoResumenRecuperacion:
        self.llamadas.append(
            (fecha_inicio, fecha_fin, fecha_hoy, agencias, asesores, cargos)
        )
        valores = {
            (date(2026, 8, 15), date(2026, 8, 25)): (10, 1000.0),
            (date(2026, 7, 1), date(2026, 7, 31)): (30, 3000.0),
            (date(2026, 7, 15), date(2026, 7, 25)): (8, 800.0),
        }
        operaciones, monto = valores[(fecha_inicio, fecha_fin)]
        return ResultadoResumenRecuperacion(
            agrupaciones={
                dimension: [
                    RecuperacionResumenAgrupada(
                        agencia="MATRIZ" if dimension == "asesor" else None,
                        dimension={
                            "agencia": "MATRIZ",
                            "asesor": "ANA ASESORA",
                            "cargo": "GESTOR DE COBRANZAS",
                            "tipo_prestamo": "MICROCREDITO",
                            "producto": "MICROCREDITO",
                            "condicion": "NUEVO",
                            "tipo_cobro": "CAPITAL",
                            "abogado": "ESTUDIO JURIDICO",
                        }[dimension],
                        numero_operaciones=operaciones,
                        monto_recuperado=monto,
                    )
                ]
                for dimension in DIMENSIONES
            },
            asesores_disponibles={"ANA ASESORA"},
            cargos_disponibles={"GESTOR DE COBRANZAS"},
        )


def test_servicio_construye_comparativo_y_todas_las_dimensiones() -> None:
    historico = FakeRecuperacionHistoricoService()
    service = ResumenRecuperacionService(historico)  # type: ignore[arg-type]

    respuesta = service.obtener_resumen(
        InputResumenRecuperacion(
            agencias=[" matriz ", "MATRIZ"],
            fecha_inicio=date(2026, 8, 15),
            fecha_fin=date(2026, 8, 25),
        ),
        auth_context(),
    )

    assert historico.llamadas == [
        (
            date(2026, 8, 15),
            date(2026, 8, 25),
            date(2026, 8, 31),
            ["MATRIZ"],
            [],
            [],
        ),
        (
            date(2026, 7, 1),
            date(2026, 7, 31),
            date(2026, 8, 31),
            ["MATRIZ"],
            [],
            [],
        ),
        (
            date(2026, 7, 15),
            date(2026, 7, 25),
            date(2026, 8, 31),
            ["MATRIZ"],
            [],
            [],
        ),
    ]
    fila = respuesta.agrupaciones.por_agencia[0]
    assert fila.numero_operaciones == 10
    assert fila.numero_operaciones_periodo_anterior == 30
    assert fila.numero_operaciones_mismo_rango_mes_anterior == 8
    assert fila.variacion_operaciones == 2
    assert fila.monto_recuperado == 1000.0
    assert fila.monto_recuperado_periodo_anterior == 3000.0
    assert fila.monto_mismo_rango_mes_anterior == 800.0
    assert fila.variacion_valor == 200.0
    assert respuesta.agrupaciones.por_asesor[0].agencia == "MATRIZ"
    assert respuesta.agrupaciones.por_cargo[0].dimension == "GESTOR DE COBRANZAS"
    assert respuesta.agrupaciones.por_tipo_cobro[0].dimension == "CAPITAL"
    assert respuesta.agrupaciones.por_abogado[0].dimension == "ESTUDIO JURIDICO"
    assert respuesta.asesores_disponibles == ["ANA ASESORA"]
    assert respuesta.cargos_disponibles == ["GESTOR DE COBRANZAS"]


def test_servicio_rechaza_fecha_posterior_a_fecha_sistema() -> None:
    service = ResumenRecuperacionService(FakeRecuperacionHistoricoService())  # type: ignore[arg-type]

    with pytest.raises(HTTPException, match="fecha_fin no puede ser posterior") as error:
        service.obtener_resumen(
            InputResumenRecuperacion(
                agencias=["MATRIZ"],
                fecha_inicio=date(2026, 9, 1),
                fecha_fin=date(2026, 9, 2),
            ),
            auth_context(),
        )

    assert error.value.status_code == 400


def test_endpoint_retorna_resumen_con_autenticacion() -> None:
    service = ResumenRecuperacionService(FakeRecuperacionHistoricoService())  # type: ignore[arg-type]
    app.dependency_overrides[get_current_auth_context] = auth_context
    app.dependency_overrides[get_resumen_recuperacion_service] = lambda: service
    try:
        response = client.post(
            "/negocios/recuperacion/resumen",
            json={
                "agencias": ["MATRIZ"],
                "fecha_inicio": "2026-08-15",
                "fecha_fin": "2026-08-25",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["fecha_inicio_periodo_anterior"] == "2026-07-01"
    assert body["fecha_fin_mismo_rango_mes_anterior"] == "2026-07-25"
    assert set(body["agrupaciones"]) == {
        "por_agencia",
        "por_asesor",
        "por_cargo",
        "por_tipo_prestamo",
        "por_producto",
        "por_condicion",
        "por_tipo_cobro",
        "por_abogado",
    }


def test_endpoint_acepta_filtros_de_asesores_y_cargos() -> None:
    service = ResumenRecuperacionService(FakeRecuperacionHistoricoService())  # type: ignore[arg-type]
    app.dependency_overrides[get_current_auth_context] = auth_context
    app.dependency_overrides[get_resumen_recuperacion_service] = lambda: service
    try:
        response = client.post(
            "/negocios/recuperacion/resumen",
            json={
                "agencias": ["MATRIZ"],
                "fecha_inicio": "2026-08-15",
                "fecha_fin": "2026-08-25",
                "asesores": ["ANA ASESORA"],
                "cargos": ["GESTOR DE COBRANZAS"],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["cargos_disponibles"] == ["GESTOR DE COBRANZAS"]


class FakeCollection:
    def __init__(self, documento=None) -> None:
        self.documento = documento
        self.pipeline = None

    def aggregate(self, pipeline, allowDiskUse=False):
        self.pipeline = pipeline
        assert allowDiskUse is True
        return [self.documento] if self.documento else []


class FakeDatabase:
    def __init__(self, historico, actual) -> None:
        self.historico = historico
        self.actual = actual

    def __getitem__(self, nombre):
        if nombre == "RecuperacionCrediticia":
            return self.historico
        if nombre == "RecuperacionCrediticiaActual":
            return self.actual
        return FakeCollection()


def test_repositorio_agrupa_dimensiones_en_un_solo_facet() -> None:
    documento = {
        "agencia": [
            {
                "dimension": "MATRIZ",
                "numero_operaciones": 2,
                "monto_recuperado": 125.5,
            }
        ],
        "asesor": [
            {
                "agencia": "MATRIZ",
                "dimension": "ANA ASESORA",
                "numero_operaciones": 2,
                "monto_recuperado": 125.5,
            }
        ],
        "cargo": [],
        "tipo_prestamo": [],
        "producto": [],
        "condicion": [],
        "tipo_cobro": [],
        "abogado": [],
        "asesores_disponibles": [{"valor": "ANA ASESORA"}],
        "cargos_disponibles": [{"valor": "GESTOR DE COBRANZAS"}],
    }
    historico = FakeCollection(documento)
    repository = MongoRecuperacionHistoricoRepository(
        FakeDatabase(historico, FakeCollection())  # type: ignore[arg-type]
    )

    resultado = repository.obtener_resumen_negocios(
        date(2026, 8, 1),
        date(2026, 8, 25),
        date(2026, 8, 31),
        ["MATRIZ"],
        ["ANA ASESORA"],
        ["GESTOR DE COBRANZAS"],
    )

    assert resultado.agrupaciones["agencia"][0].monto_recuperado == 125.5
    assert resultado.agrupaciones["asesor"][0].agencia == "MATRIZ"
    assert resultado.asesores_disponibles == {"ANA ASESORA"}
    assert resultado.cargos_disponibles == {"GESTOR DE COBRANZAS"}
    facet = next(etapa["$facet"] for etapa in historico.pipeline if "$facet" in etapa)
    assert set(facet) == {*DIMENSIONES, "asesores_disponibles", "cargos_disponibles"}
    assert facet["agencia"][:2] == [
        {"$match": {"asesor": {"$in": ["ANA ASESORA"]}}},
        {"$match": {"cargo": {"$in": ["GESTOR DE COBRANZAS"]}}},
    ]
    assert historico.pipeline[0] == {
        "$match": {"fecha_corte": {"$gte": "20260801", "$lte": "20260825"}}
    }
