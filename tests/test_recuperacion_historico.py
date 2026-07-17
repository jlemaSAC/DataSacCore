from datetime import date

import pytest

from app.modules.analytic.recuperacion.recuperacion_historico.repositories.mongo_recuperacion_historico_repository import (
    MongoRecuperacionHistoricoRepository,
)
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.sql_recuperacion_historico_repository import (
    SqlRecuperacionHistoricoRepository,
)
from app.modules.analytic.recuperacion.recuperacion_historico.domain import (
    PrestamoRecuperacion,
    RecuperacionEtiquetada,
)
from app.modules.analytic.recuperacion.recuperacion_historico.schemas import (
    InputRecuperacionHistoricoRango,
)
from app.modules.analytic.recuperacion.recuperacion_historico.service import RecuperacionHistoricoService


class FakeCollection:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.pipeline = None

    def aggregate(self, pipeline, allowDiskUse=False):
        self.pipeline = pipeline
        assert allowDiskUse is True
        return self.rows


class FakeSituacionCollection:
    def __init__(self) -> None:
        self.calls = []

    def find(self, query, projection):
        self.calls.append((query, projection))
        if query.get("fecha_corte") == "20260601":
            return [
                {
                    "NumeroPrestamo": "2020112000639",
                    "EstadoPrestamo": "Al dia",
                    "Calificacion": "A-1",
                }
            ]
        return [
            {
                "NumeroPrestamo": "2020112000639",
                "Agencia": "Matriz",
                "TipoCondicion": "Nuevo",
                "TipoPrestamo": "Microcredito",
                "Producto": "MICROCREDITO",
                "Segmento": "Minorista",
                "NombreAsesor": "Ana Asesora",
                "Provincia": "Tungurahua",
                "Canton": "Ambato",
                "Parroquia": "La Matriz",
                "Educacion": "Superior",
                "Edad": 35,
                "TipoDeGarantia": "Sobre firmas",
                "DeudaInicial": 12000,
                "TasaNominal": 14.95,
                "TasaAnual": 16.01,
                "Plazo": 36,
                "EstadoPrestamo": "En mora",
                "Calificacion": "C-1",
            }
        ]


class FakeDatabase:
    def __init__(self, historico_collection, actual_collection=None):
        self.historico_collection = historico_collection
        self.actual_collection = actual_collection or FakeCollection()
        self.situacion_collection = FakeSituacionCollection()
        self.situacion_actual_collection = FakeSituacionCollection()

    def __getitem__(self, name):
        if name == "RecuperacionCrediticia":
            return self.historico_collection
        if name == "RecuperacionCrediticiaActual":
            return self.actual_collection
        if name == "SituacionCrediticia":
            return self.situacion_collection
        assert name == "SituacionCrediticiaActual"
        return self.situacion_actual_collection


def test_etiqueta_columnas_de_cobro_sin_lookup() -> None:
    collection = FakeCollection([
        {
            "fecha_corte": "20260601",
            "numero_prestamo": "2020112000639",
            "agencia": "MATRIZ",
            "tipo_transaccion": "ABONO PRESTAMO AUTOMATICO",
            "tipo_cobro": "COBRANZA",
            "valor_recuperado": 0.01,
            "es_cancelado_anterior_cobro": False,
            "es_cancelado_actual_cobro": True,
            "se_cancelo_con_el_cobro": True,
            "fecha_estado_prestamo_anterior_cobro": "20260531",
            "fecha_estado_prestamo_actual_cobro": "20260601",
        }
    ])
    repository = MongoRecuperacionHistoricoRepository(FakeDatabase(collection))  # type: ignore[arg-type]

    resultado = repository.obtener_recuperaciones(
        InputRecuperacionHistoricoRango(
            fecha_desde=date(2026, 6, 1), fecha_hasta=date(2026, 6, 1)
        ),
        date(2026, 6, 2),
    )

    assert resultado[0].tipo_cobro == "COBRANZA"
    assert resultado[0].tipo_transaccion == "ABONO PRESTAMO AUTOMATICO"
    assert resultado[0].valor_recuperado == 0.01
    assert resultado[0].agencia == "MATRIZ"
    assert resultado[0].es_actual is False
    assert resultado[0].es_cancelado_anterior_cobro is False
    assert resultado[0].es_cancelado_actual_cobro is True
    assert resultado[0].se_cancelo_con_el_cobro is True
    assert resultado[0].fecha_estado_prestamo_anterior_cobro == "20260531"
    assert resultado[0].fecha_estado_prestamo_actual_cobro == "20260601"
    assert collection.pipeline[0] == {
        "$match": {"fecha_corte": {"$gte": "20260601", "$lte": "20260601"}}
    }
    assert not any("$lookup" in stage or "$group" in stage for stage in collection.pipeline)
    assert any(stage == {"$unwind": "$cobros"} for stage in collection.pipeline)
    cobros = collection.pipeline[1]["$project"]["cobros"]
    assert cobros[0]["valor"] == {
        "$convert": {"input": "$CAPITAL", "to": "double", "onError": 0, "onNull": 0}
    }


def test_consulta_estados_y_dimensiones_del_corte_final_por_prestamo() -> None:
    collection = FakeCollection()
    database = FakeDatabase(collection)
    repository = MongoRecuperacionHistoricoRepository(database)  # type: ignore[arg-type]

    resultado = repository.obtener_prestamos_por_numero(
        {"2020112000639"},
        fecha_inicio="20260601",
        fecha_fin="20260712",
        fecha_actual="20260715",
    )

    prestamo = resultado["2020112000639"]
    assert prestamo.agencia == "MATRIZ"
    assert prestamo.estado_prestamo_inicio == "AL DIA"
    assert prestamo.estado_prestamo_fin == "EN MORA"
    assert prestamo.calificacion_inicio == "A-1"
    assert prestamo.calificacion_fin == "C-1"
    assert prestamo.monto == 12000.0
    assert prestamo.tasa == 14.95
    assert prestamo.plazo == 36
    assert len(database.situacion_collection.calls) == 2
    assert database.situacion_collection.calls[0][0] == {
        "NumeroPrestamo": {"$in": ["2020112000639"]},
        "fecha_corte": "20260601",
    }
    assert database.situacion_collection.calls[1][0] == {
        "NumeroPrestamo": {"$in": ["2020112000639"]},
        "fecha_corte": "20260712",
    }


def test_consulta_fecha_actual_desde_recuperacion_crediticia_actual() -> None:
    actual_collection = FakeCollection([
        {
            "fecha_corte": "20260601",
            "numero_prestamo": "2020112000639",
            "tipo_transaccion": "ABONO",
            "tipo_cobro": "CAPITAL",
            "valor_recuperado": 12.5,
        }
    ])
    historico_collection = FakeCollection()
    repository = MongoRecuperacionHistoricoRepository(
        FakeDatabase(historico_collection, actual_collection)  # type: ignore[arg-type]
    )

    resultado = repository.obtener_recuperaciones(
        InputRecuperacionHistoricoRango(
            fecha_desde=date(2026, 6, 1), fecha_hasta=date(2026, 6, 1)
        ),
        date(2026, 6, 1),
    )

    assert resultado[0].es_actual is True
    assert actual_collection.pipeline[0] == {
        "$match": {"fecha_corte": {"$gte": "20260601", "$lte": "20260601"}}
    }
    assert historico_collection.pipeline is None


class FakeSituacionActualParcial:
    def __init__(self) -> None:
        self.calls = []

    def find(self, query, projection):
        self.calls.append((query, projection))
        numeros = set(query["NumeroPrestamo"]["$in"])
        if "PRESTAMO_ACTUAL" not in numeros:
            return []
        return [
            {
                "NumeroPrestamo": "PRESTAMO_ACTUAL",
                "Agencia": "Matriz",
                "TipoCondicion": "Nuevo",
                "TipoPrestamo": "Microcredito actual",
                "Producto": "Microcredito",
                "Segmento": "Minorista",
                "NombreAsesor": "Ana Actual",
                "Provincia": "Tungurahua",
                "Canton": "Ambato",
                "Parroquia": "La Matriz",
                "Educacion": "Superior",
                "Edad": 35,
                "TipoDeGarantia": "Sobre firmas",
                "DeudaInicial": 12000,
                "TasaNominal": 14.95,
                "TasaAnual": 16.01,
                "Plazo": 36,
                "EstadoPrestamo": "Al dia",
                "Calificacion": "A-1",
            }
        ]


class FakeSituacionHistoricaAnterior:
    def __init__(self) -> None:
        self.calls = []

    def find(self, query, projection):
        self.calls.append((query, projection))
        if query.get("fecha_corte") != "20260630":
            return []
        numeros = set(query["NumeroPrestamo"]["$in"])
        if "PRESTAMO_FALTANTE" not in numeros:
            return []
        return [
            {
                "NumeroPrestamo": "PRESTAMO_FALTANTE",
                "Agencia": "Latacunga",
                "TipoCondicion": "Renovado",
                "TipoPrestamo": "Consumo prioritario",
                "Producto": "Consumo",
                "Segmento": "Consumo",
                "NombreAsesor": "Luis Historico",
                "Provincia": "Cotopaxi",
                "Canton": "Latacunga",
                "Parroquia": "Juan Montalvo",
                "Educacion": "Secundaria",
                "Edad": 42,
                "TipoDeGarantia": "Hipotecaria",
                "DeudaInicial": 8000,
                "TasaNominal": 15.5,
                "TasaAnual": 16.7,
                "Plazo": 48,
                "EstadoPrestamo": "En mora",
                "Calificacion": "C-1",
            }
        ]


class FakeFallbackDatabase:
    def __init__(self) -> None:
        self.recuperacion = FakeCollection()
        self.recuperacion_actual = FakeCollection()
        self.situacion = FakeSituacionHistoricaAnterior()
        self.situacion_actual = FakeSituacionActualParcial()

    def __getitem__(self, name):
        if name == "RecuperacionCrediticia":
            return self.recuperacion
        if name == "RecuperacionCrediticiaActual":
            return self.recuperacion_actual
        if name == "SituacionCrediticia":
            return self.situacion
        assert name == "SituacionCrediticiaActual"
        return self.situacion_actual


def test_fecha_actual_completa_prestamos_faltantes_con_situacion_del_dia_anterior() -> None:
    database = FakeFallbackDatabase()
    repository = MongoRecuperacionHistoricoRepository(database)  # type: ignore[arg-type]

    resultado = repository.obtener_prestamos_por_numero(
        {"PRESTAMO_ACTUAL", "PRESTAMO_FALTANTE"},
        fecha_inicio="20260701",
        fecha_fin="20260701",
        fecha_actual="20260701",
    )

    assert resultado["PRESTAMO_ACTUAL"].agencia == "MATRIZ"
    assert resultado["PRESTAMO_FALTANTE"].agencia == "LATACUNGA"
    assert resultado["PRESTAMO_FALTANTE"].tipo_prestamo == "CONSUMO PRIORITARIO"
    assert resultado["PRESTAMO_FALTANTE"].calificacion_fin == "C-1"
    assert any(call[0].get("fecha_corte") == "20260630" for call in database.situacion.calls)


def test_entrada_solo_admite_fechas() -> None:
    with pytest.raises(ValueError, match="Extra inputs"):
        InputRecuperacionHistoricoRango(
            fecha_desde=date(2026, 6, 1),
            fecha_hasta=date(2026, 6, 1),
            group_by=["tipo_cobro"],
        )


class FakeSqlResult:
    def mappings(self):
        return self

    def __iter__(self):
        return iter([{"NumeroPrestamo": "2020112000639", "Agencia": "Matriz"}])


class FakeSqlSession:
    def __init__(self) -> None:
        self.params = None

    def execute(self, statement, params):
        self.params = params
        assert "FROM COLOCACION.PRESTAMO" in str(statement)
        return FakeSqlResult()


def test_consulta_actual_sql_se_limita_a_los_numeros_recuperados() -> None:
    session = FakeSqlSession()
    repository = SqlRecuperacionHistoricoRepository(session)  # type: ignore[arg-type]

    resultado = repository.obtener_prestamos_actuales({"2020112000639"})

    assert session.params == {"numeros_prestamo": ["2020112000639"]}
    assert resultado["2020112000639"]["Agencia"] == "Matriz"


def test_respuesta_indexa_el_prestamo_y_las_recuperaciones_lo_referencian() -> None:
    numero_prestamo = "2020112000639"
    prestamo = PrestamoRecuperacion(
        numero_prestamo=numero_prestamo,
        agencia="MATRIZ",
        condicion="NUEVO",
        tipo_prestamo="MICROCREDITO",
        producto="MICROCREDITO",
        segmento="MINORISTA",
        asesor="ANA ASESORA",
        provincia="TUNGURAHUA",
        canton="AMBATO",
        parroquia="LA MATRIZ",
        educacion="SUPERIOR",
        edad=35,
        garantia="SOBRE FIRMAS",
        monto=12000.0,
        tasa=14.95,
        tasa_real=16.01,
        plazo=36,
        estado_prestamo_inicio="AL DIA",
        estado_prestamo_fin="EN MORA",
    )

    respuesta = RecuperacionHistoricoService._construir_respuesta(
        InputRecuperacionHistoricoRango(
            fecha_desde=date(2026, 6, 1), fecha_hasta=date(2026, 6, 1)
        ),
        [
            RecuperacionEtiquetada(
                fecha_cobro=date(2026, 6, 1),
                numero_prestamo=numero_prestamo,
                tipo_cobro="CAPITAL",
                tipo_transaccion="ABONO",
                valor_recuperado=120.5,
            )
        ],
        {numero_prestamo: prestamo},
    )

    assert set(respuesta.model_dump().keys()) == {"prestamos_por_numero", "recuperaciones"}
    assert respuesta.prestamos_por_numero[numero_prestamo].estado_prestamo_fin == "EN MORA"
    assert set(respuesta.prestamos_por_numero[numero_prestamo].model_dump().keys()) == {
        "numero_prestamo",
        "agencia",
        "condicion",
        "tipo_prestamo",
        "producto",
        "segmento",
        "asesor",
        "provincia",
        "canton",
        "parroquia",
        "educacion",
        "edad",
        "garantia",
        "monto",
        "tasa",
        "tasa_real",
        "plazo",
        "estado_prestamo_inicio",
        "estado_prestamo_fin",
        "calificacion_inicio",
        "calificacion_fin",
    }
    assert respuesta.prestamos_por_numero[numero_prestamo].tipo_prestamo == "MICROCREDITO"
    assert respuesta.prestamos_por_numero[numero_prestamo].condicion == "NUEVO"
    assert respuesta.prestamos_por_numero[numero_prestamo].monto == 12000.0
    assert respuesta.recuperaciones[0].numero_prestamo == numero_prestamo
    assert respuesta.recuperaciones[0].valor_recuperado == 120.5
    assert "fecha_cobro" not in respuesta.recuperaciones[0].model_dump()
    assert "periodo" not in respuesta.recuperaciones[0].model_dump()


def test_movimiento_actual_usa_el_complemento_solo_cuando_no_tiene_contexto() -> None:
    numero_prestamo = "2020112000639"
    prestamo = PrestamoRecuperacion(
        numero_prestamo=numero_prestamo,
        agencia="MATRIZ",
        condicion="SIN DATOS",
        tipo_prestamo="SIN DATOS",
        producto="SIN DATOS",
        segmento="SIN DATOS",
        asesor="ANA ASESORA",
        provincia="SIN DATOS",
        canton="SIN DATOS",
        parroquia="SIN DATOS",
        educacion="SIN DATOS",
        edad=None,
        garantia="SIN DATOS",
        monto=None,
        tasa=None,
        tasa_real=None,
        plazo=None,
        estado_prestamo_inicio="AL DIA",
        estado_prestamo_fin="AL DIA",
        calificacion_inicio="A-1",
        calificacion_fin="A-1",
    )

    respuesta = RecuperacionHistoricoService._construir_respuesta(
        InputRecuperacionHistoricoRango(
            fecha_desde=date(2026, 6, 1), fecha_hasta=date(2026, 6, 1)
        ),
        [
            RecuperacionEtiquetada(
                fecha_cobro=date(2026, 6, 1),
                numero_prestamo=numero_prestamo,
                tipo_cobro="CAPITAL",
                tipo_transaccion="ABONO",
                valor_recuperado=20,
                es_actual=True,
            )
        ],
        {numero_prestamo: prestamo},
    )

    movimiento = respuesta.recuperaciones[0]
    assert movimiento.agencia == "MATRIZ"
    assert movimiento.asesor == "ANA ASESORA"
    assert movimiento.estado_prestamo_anterior_cobro == "AL DIA"
    assert movimiento.estado_prestamo_actual_cobro == "AL DIA"
    assert movimiento.calificacion_anterior_cobro == "A-1"
    assert movimiento.calificacion_actual_cobro == "A-1"


class FakeUsuario:
    fecha_sistema = date(2026, 6, 1)


class FakeAuthContext:
    usuario = FakeUsuario()


class FakeMongoServiceRepository:
    def __init__(self) -> None:
        self.prestamos_args = None

    def obtener_recuperaciones(self, input_data, fecha_hoy):
        assert fecha_hoy == date(2026, 6, 1)
        return [
            RecuperacionEtiquetada(
                fecha_cobro=date(2026, 6, 1),
                numero_prestamo="2020112000639",
                tipo_cobro="CAPITAL",
                tipo_transaccion="ABONO",
                valor_recuperado=10,
                es_actual=True,
            )
        ]

    def obtener_prestamos_por_numero(self, numeros_prestamo, fecha_inicio, fecha_fin, fecha_actual):
        self.prestamos_args = (numeros_prestamo, fecha_inicio, fecha_fin, fecha_actual)
        return {
            "2020112000639": PrestamoRecuperacion(
                numero_prestamo="2020112000639",
                agencia="MATRIZ",
                condicion="NUEVO",
                tipo_prestamo="MICROCREDITO",
                producto="MICROCREDITO",
                segmento="MINORISTA",
                asesor="ANA ASESORA",
                provincia="TUNGURAHUA",
                canton="AMBATO",
                parroquia="LA MATRIZ",
                educacion="SUPERIOR",
                edad=35,
                garantia="SOBRE FIRMAS",
                monto=12000,
                tasa=14.95,
                tasa_real=16.01,
                plazo=36,
                estado_prestamo_inicio="AL DIA",
                estado_prestamo_fin="AL DIA",
            )
        }


class FakeSqlShouldNotRun:
    def obtener_prestamos_actuales(self, numeros_prestamo):
        raise AssertionError("No debe consultar SQL para fecha actual")


def test_service_fecha_actual_usa_solo_mongo_para_prestamos() -> None:
    mongo = FakeMongoServiceRepository()
    service = RecuperacionHistoricoService(
        mongo_repository=mongo,  # type: ignore[arg-type]
        sql_repository=FakeSqlShouldNotRun(),  # type: ignore[arg-type]
    )

    respuesta = service.obtener_recuperacion_por_rango(
        InputRecuperacionHistoricoRango(
            fecha_desde=date(2026, 6, 1),
            fecha_hasta=date(2026, 6, 1),
        ),
        FakeAuthContext(),  # type: ignore[arg-type]
    )

    assert mongo.prestamos_args == (
        {"2020112000639"},
        "20260601",
        "20260601",
        "20260601",
    )
    assert respuesta.recuperaciones[0].agencia == "MATRIZ"
