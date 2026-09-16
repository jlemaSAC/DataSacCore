from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.modules.analytic.recuperacion.recuperacion_historico.domain import (
    CuboFiltroRecuperacion,
    DesgloseCobroRecuperacion,
    DetalleRecuperacionAgrupado,
    RecuperacionResumenAgrupada,
    ResultadoDetalleRecuperacion,
    ResultadoResumenRecuperacion,
)
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.mongo_recuperacion_historico_repository import (
    MongoRecuperacionHistoricoRepository,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext, UsuarioTokenPayload
from app.modules.negocios.recuperacion.resumen.dependencies import (
    get_detalle_resumen_recuperacion_service,
    get_resumen_recuperacion_service,
)
from app.modules.negocios.recuperacion.resumen.domain import DatosOperativosRecuperacion
from app.modules.negocios.recuperacion.resumen.schemas import (
    InputDetalleResumenRecuperacion,
    InputResumenRecuperacion,
)
from app.modules.negocios.recuperacion.resumen.repositories.sql_detalle_recuperacion_repository import (
    SqlDetalleRecuperacionRepository,
)
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
        incluir_desglose_cobros=False,
    ) -> ResultadoResumenRecuperacion:
        self.llamadas.append(
            (
                fecha_inicio,
                fecha_fin,
                fecha_hoy,
                agencias,
                incluir_desglose_cobros,
            )
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
            cubos_filtro=[
                CuboFiltroRecuperacion(
                    tipo_dimension="agencia",
                    dimension="MATRIZ",
                    agencia=None,
                    asesor="ANA ASESORA",
                    cargo="GESTOR DE COBRANZAS",
                    numero_operaciones=operaciones,
                    monto_recuperado=monto,
                )
            ],
            desglose_cobros=(
                [
                    DesgloseCobroRecuperacion(
                        tipo_dimension="agencia",
                        dimension="MATRIZ",
                        agencia=None,
                        asesor="ANA ASESORA",
                        cargo="GESTOR DE COBRANZAS",
                        tipo_cobro="CAPITAL",
                        numero_rubros=7,
                        monto_recuperado=700.0,
                    )
                ]
                if incluir_desglose_cobros
                else []
            ),
        )

    def obtener_detalle_resumen_por_rango(self, **kwargs) -> ResultadoDetalleRecuperacion:
        self.llamadas.append(("detalle", kwargs))
        return ResultadoDetalleRecuperacion(
            items=[
                DetalleRecuperacionAgrupado(
                    numero_prestamo="2026040208325",
                    fecha_ultimo_cobro=date(2026, 8, 15),
                    total_recuperado_periodo=2260.52,
                )
            ],
            total_registros=21,
            total_recuperado_periodo=5082383.30,
        )


class FakeDetalleSqlRepository:
    def __init__(self) -> None:
        self.numeros: list[str] = []

    def obtener_datos_actuales(self, numeros_prestamo):
        self.numeros = numeros_prestamo
        return {
            "2026040208325": DatosOperativosRecuperacion(
                numero_prestamo="2026040208325",
                socio=12,
                nombre="TOALOMBO CHIMBORAZO JOSE SEGUNDO",
                estado_prestamo="AL DIA",
                calificacion_actual="A-1",
                saldo_capital=17024.46,
                pendiente_pago=0,
                valor_al_dia_mas_cuota_actual=2214.21,
                cuotas_pagadas=4,
                total_cuotas=12,
                es_diferido=False,
            )
        }


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
            True,
        ),
        (
            date(2026, 7, 1),
            date(2026, 7, 31),
            date(2026, 8, 31),
            ["MATRIZ"],
            False,
        ),
        (
            date(2026, 7, 15),
            date(2026, 7, 25),
            date(2026, 8, 31),
            ["MATRIZ"],
            False,
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
    assert {cubo.periodo for cubo in respuesta.cubos_filtro} == {
        "actual",
        "anterior",
        "mismo_rango_anterior",
    }
    assert respuesta.desglose_cobros[0].tipo_cobro == "CAPITAL"
    assert respuesta.desglose_cobros[0].numero_rubros == 7


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


def test_endpoint_entrega_hechos_para_filtrar_en_frontend() -> None:
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
    assert response.json()["cargos_disponibles"] == ["GESTOR DE COBRANZAS"]
    assert len(response.json()["cubos_filtro"]) == 3


def test_servicio_detalle_pagina_en_mongo_y_enriquece_solo_la_pagina() -> None:
    historico = FakeRecuperacionHistoricoService()
    sql = FakeDetalleSqlRepository()
    service = ResumenRecuperacionService(historico, sql)  # type: ignore[arg-type]

    respuesta = service.obtener_detalle(
        InputDetalleResumenRecuperacion(
            agencias=["matriz"],
            fecha_inicio=date(2026, 8, 1),
            fecha_fin=date(2026, 8, 31),
            dimension="agencia",
            valor_dimension="matriz",
            asesores=["ana asesora"],
            cargos=["gestor de cobranzas"],
            pagina=2,
            tamano_pagina=20,
        ),
        auth_context(),
    )

    assert sql.numeros == ["2026040208325"]
    assert historico.llamadas[-1][1]["offset"] == 20
    assert historico.llamadas[-1][1]["limite"] == 20
    assert historico.llamadas[-1][1]["asesores"] == ["ANA ASESORA"]
    assert respuesta.total_registros == 21
    assert respuesta.total_paginas == 2
    assert respuesta.total_recuperado_mes == 5082383.30
    assert respuesta.items[0].estado_prestamo == "AL DIA"
    assert respuesta.items[0].total_recuperado_mes == 2260.52
    assert respuesta.totales_pagina.saldo_capital == 17024.46


def test_endpoint_retorna_detalle_operativo_paginado() -> None:
    service = ResumenRecuperacionService(
        FakeRecuperacionHistoricoService(),  # type: ignore[arg-type]
        FakeDetalleSqlRepository(),  # type: ignore[arg-type]
    )
    app.dependency_overrides[get_current_auth_context] = auth_context
    app.dependency_overrides[get_detalle_resumen_recuperacion_service] = lambda: service
    try:
        response = client.post(
            "/negocios/recuperacion/resumen/detalle",
            json={
                "agencias": ["MATRIZ"],
                "fecha_inicio": "2026-08-01",
                "fecha_fin": "2026-08-31",
                "dimension": "producto",
                "valor_dimension": "MICROCREDITO",
                "pagina": 1,
                "tamano_pagina": 100,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["socio"] == 12
    assert body["items"][0]["calificacion_actual"] == "A-1"
    assert body["items"][0]["es_diferido"] is False
    assert body["total_registros"] == 21


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
        "desglose_cobros": [
            {
                "tipo_dimension": "agencia",
                "dimension": "MATRIZ",
                "agencia": None,
                "asesor": "ANA ASESORA",
                "cargo": "GESTOR DE COBRANZAS",
                "tipo_cobro": "CAPITAL",
                "numero_rubros": 2,
                "monto_recuperado": 125.5,
            }
        ],
        "filtro_agencia": [
            {
                "dimension": "MATRIZ",
                "asesor": "ANA ASESORA",
                "cargo": "GESTOR DE COBRANZAS",
                "numero_operaciones": 2,
                "monto_recuperado": 125.5,
            }
        ],
        **{f"filtro_{dimension}": [] for dimension in DIMENSIONES if dimension != "agencia"},
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
        True,
    )

    assert resultado.agrupaciones["agencia"][0].monto_recuperado == 125.5
    assert resultado.agrupaciones["asesor"][0].agencia == "MATRIZ"
    assert resultado.asesores_disponibles == {"ANA ASESORA"}
    assert resultado.cargos_disponibles == {"GESTOR DE COBRANZAS"}
    assert resultado.cubos_filtro[0].dimension == "MATRIZ"
    assert resultado.desglose_cobros[0].numero_rubros == 2
    facet = next(etapa["$facet"] for etapa in historico.pipeline if "$facet" in etapa)
    assert set(facet) == {
        *DIMENSIONES,
        "asesores_disponibles",
        "cargos_disponibles",
        "desglose_cobros",
        *(f"filtro_{dimension}" for dimension in DIMENSIONES),
    }
    assert historico.pipeline[0] == {
        "$match": {"fecha_corte": {"$gte": "20260801", "$lte": "20260825"}}
    }


def test_repositorio_detalle_une_hoy_y_pagina_despues_de_filtrar() -> None:
    documento = {
        "estadisticas": [
            {"total_registros": 1, "total_recuperado_periodo": 125.5}
        ],
        "items": [
            {
                "numero_prestamo": "2026040208325",
                "fecha_ultimo_cobro": "20260831",
                "total_recuperado_periodo": 125.5,
            }
        ],
    }
    historico = FakeCollection(documento)
    repository = MongoRecuperacionHistoricoRepository(
        FakeDatabase(historico, FakeCollection())  # type: ignore[arg-type]
    )

    resultado = repository.obtener_detalle_resumen_negocios(
        fecha_desde=date(2026, 8, 1),
        fecha_hasta=date(2026, 8, 31),
        fecha_actual=date(2026, 8, 31),
        agencias=["MATR"],
        dimension="cargo",
        valor_dimension="GESTOR DE COBRANZAS",
        asesores=["ANA ASESORA"],
        cargos=[],
        offset=20,
        limite=20,
    )

    assert resultado.total_registros == 1
    assert resultado.items[0].fecha_ultimo_cobro == date(2026, 8, 31)
    assert any("$unionWith" in etapa for etapa in historico.pipeline)
    facet = next(etapa["$facet"] for etapa in historico.pipeline if "$facet" in etapa)
    assert facet["items"][1:] == [
        {"$skip": 20},
        {"$limit": 20},
        {
            "$project": {
                "_id": 0,
                "numero_prestamo": "$_id",
                "fecha_ultimo_cobro": 1,
                "total_recuperado_periodo": 1,
            }
        },
    ]


class FakeSqlResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def mappings(self):
        return self.rows


class FakeSqlSession:
    def __init__(self, rows) -> None:
        self.rows = rows
        self.params = None
        self.statement = None

    def execute(self, statement, params):
        self.statement = statement
        self.params = params
        return FakeSqlResult(self.rows)


def test_repositorio_sql_consulta_solo_los_prestamos_de_la_pagina() -> None:
    db = FakeSqlSession(
        [
            {
                "NumeroPrestamo": "2026040208325",
                "NumeroSocio": 12,
                "Nombre": "JOSE TOALOMBO",
                "EstadoPrestamo": "AL DIA",
                "CalificacionActual": "A-1",
                "SaldoCapital": 17024.46,
                "PendientePago": 0,
                "ValorAlDiaMasCuotaActual": 2214.21,
                "CuotasPagadas": 4,
                "TotalCuotas": 12,
                "EsDiferido": 0,
            }
        ]
    )
    repository = SqlDetalleRecuperacionRepository(db)  # type: ignore[arg-type]

    resultado = repository.obtener_datos_actuales(["2026040208325"])

    assert db.params == {"numeros_prestamo": ["2026040208325"]}
    assert "WITH PrestamosPagina" in str(db.statement)
    assert resultado["2026040208325"].estado_prestamo == "AL DIA"
    assert resultado["2026040208325"].valor_al_dia_mas_cuota_actual == 2214.21
