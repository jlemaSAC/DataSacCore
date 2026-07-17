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
    InputRecuperacionHistoricoAgrupado,
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

    respuesta_serializada = respuesta.model_dump(by_alias=True, exclude_none=True)
    assert set(respuesta_serializada.keys()) == {"p", "r"}
    assert set(respuesta_serializada["p"][numero_prestamo]) == {
        "co",
        "tp",
        "pr",
        "sg",
        "pv",
        "cn",
        "pq",
        "ed",
        "e",
        "ga",
        "mo",
        "tn",
        "tr",
        "pl",
    }
    assert set(respuesta_serializada["r"][0]) == {
        "an",
        "me",
        "np",
        "tc",
        "tx",
        "v",
        "ag",
        "as",
        "ea",
        "ec",
        "ca",
        "cc",
    }
    assert respuesta.prestamos_por_numero[numero_prestamo].tipo_prestamo == "MICROCREDITO"
    assert respuesta.prestamos_por_numero[numero_prestamo].condicion == "NUEVO"
    assert respuesta.prestamos_por_numero[numero_prestamo].monto == 12000.0
    assert respuesta.recuperaciones[0].numero_prestamo == numero_prestamo
    assert respuesta.recuperaciones[0].valor == 120.5
    assert respuesta.recuperaciones[0].transaccion == "ABONO"
    movimiento_serializado = respuesta.recuperaciones[0].model_dump()
    assert "tipo_transaccion" not in movimiento_serializado
    assert "valor_recuperado" not in movimiento_serializado
    assert "estado_prestamo_anterior_cobro" not in movimiento_serializado
    assert "estado_prestamo_actual_cobro" not in movimiento_serializado
    assert "calificacion_anterior_cobro" not in movimiento_serializado
    assert "calificacion_actual_cobro" not in movimiento_serializado
    assert respuesta.recuperaciones[0].abogado_externo is None
    assert respuesta.recuperaciones[0].nombre_cobranza_apoyo is None
    assert "abogado_externo" not in respuesta.recuperaciones[0].model_dump(exclude_none=True)
    assert "nombre_cobranza_apoyo" not in respuesta.recuperaciones[0].model_dump(exclude_none=True)
    assert "numero_prestamo" not in respuesta.prestamos_por_numero[numero_prestamo].model_dump()
    assert "estado_prestamo_inicio" not in respuesta.prestamos_por_numero[numero_prestamo].model_dump()
    assert "estado_prestamo_fin" not in respuesta.prestamos_por_numero[numero_prestamo].model_dump()
    assert "calificacion_inicio" not in respuesta.prestamos_por_numero[numero_prestamo].model_dump()
    assert "calificacion_fin" not in respuesta.prestamos_por_numero[numero_prestamo].model_dump()
    assert "agencia" not in respuesta.prestamos_por_numero[numero_prestamo].model_dump()
    assert "asesor" not in respuesta.prestamos_por_numero[numero_prestamo].model_dump()


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
    assert movimiento.estado_anterior == "AL DIA"
    assert movimiento.estado_actual == "AL DIA"
    assert movimiento.calificacion_anterior == "A-1"
    assert movimiento.calificacion_actual == "A-1"


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


def test_service_compacto_indexa_textos_y_montos() -> None:
    service = RecuperacionHistoricoService(
        mongo_repository=FakeMongoServiceRepository(),  # type: ignore[arg-type]
    )

    respuesta = service.obtener_recuperacion_compacta(
        InputRecuperacionHistoricoRango(
            fecha_desde=date(2026, 6, 1), fecha_hasta=date(2026, 6, 1)
        ),
        FakeAuthContext(),  # type: ignore[arg-type]
    )

    assert respuesta.formato == "recuperacion-compacta-v2"
    assert respuesta.periodos == ["2026-06"]
    assert respuesta.prestamos[0][0] == "2020112000639"
    assert respuesta.prestamos[0][13] == 1200000
    assert respuesta.recuperaciones[0][4] == 1000
    assert respuesta.catalogos.agencias[respuesta.recuperaciones[0][5]] == "MATRIZ"
    assert respuesta.resumen.cantidad_prestamos == 1
    assert respuesta.resumen.cantidad_recuperaciones == 1


def test_entrada_agrupada_normaliza_filtros_y_valida_dimension() -> None:
    entrada = InputRecuperacionHistoricoAgrupado(
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 12, 31),
        dimension="asesor",
        agencias=[" Matriz ", "MATRIZ"],
        asesores=["Ana Asesora"],
        tipos_prestamo=["Microcredito"],
    )

    assert entrada.agencias == ["MATRIZ"]
    assert entrada.asesores == ["ANA ASESORA"]
    assert entrada.tipos_prestamo == ["MICROCREDITO"]
    with pytest.raises(ValueError):
        InputRecuperacionHistoricoAgrupado(
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
            dimension="campo_sql_invalido",
        )


def test_pipeline_agrupado_consolida_antes_del_lookup_y_aplica_filtros_en_facet() -> None:
    entrada = InputRecuperacionHistoricoAgrupado(
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 12, 31),
        dimension="tipo_cobro",
        agencias=["MATRIZ"],
        asesores=["ANA ASESORA"],
        tipos_prestamo=["MICROCREDITO"],
    )

    pipeline = MongoRecuperacionHistoricoRepository._construir_pipeline_agrupado(
        entrada,
        "20260101",
        "20261231",
        "20270101",
    )

    primer_lookup = next(i for i, stage in enumerate(pipeline) if "$lookup" in stage)
    grupos_antes_lookup = [stage for stage in pipeline[:primer_lookup] if "$group" in stage]
    assert len(grupos_antes_lookup) == 2
    assert grupos_antes_lookup[0]["$group"]["_id"]["dimension"] == "$cobros.tipo_cobro"
    assert "periodos" in grupos_antes_lookup[1]["$group"]
    facet = next(stage["$facet"] for stage in pipeline if "$facet" in stage)
    assert {"$unwind": "$periodos"} in facet["datos"]
    assert {"$match": {"agencia": {"$in": ["MATRIZ"]}}} in facet["datos"]
    assert {"$match": {"asesor": {"$in": ["ANA ASESORA"]}}} in facet["datos"]
    assert {
        "$match": {"tipo_prestamo": {"$in": ["MICROCREDITO"]}}
    } in facet["datos"]


class FakeMongoAgrupadoRepository:
    def obtener_recuperacion_agrupada(self, input_data, fecha_hoy):
        assert fecha_hoy == date(2026, 6, 1)
        assert input_data.dimension == "asesor"
        return {
            "datos": [
                {
                    "periodo": "202601",
                    "etiqueta": "ANA ASESORA",
                    "valor": 100.5,
                    "cantidad_movimientos": 2,
                },
                {
                    "periodo": "202602",
                    "etiqueta": "ANA ASESORA",
                    "valor": 80,
                    "cantidad_movimientos": 1,
                },
                {
                    "periodo": "202602",
                    "etiqueta": "LUIS ASESOR",
                    "valor": 20,
                    "cantidad_movimientos": 1,
                },
            ],
            "agencias": ["MATRIZ"],
            "asesores": ["ANA ASESORA", "LUIS ASESOR"],
            "tipos_prestamo": ["MICROCREDITO"],
        }


def test_service_agrupado_construye_matriz_mensual_y_totales() -> None:
    service = RecuperacionHistoricoService(
        mongo_repository=FakeMongoAgrupadoRepository(),  # type: ignore[arg-type]
    )
    entrada = InputRecuperacionHistoricoAgrupado(
        fecha_desde=date(2026, 1, 1),
        fecha_hasta=date(2026, 6, 1),
        dimension="asesor",
    )

    respuesta = service.obtener_recuperacion_agrupada(
        entrada,
        FakeAuthContext(),  # type: ignore[arg-type]
    )

    assert [periodo.clave for periodo in respuesta.periodos] == ["2026-01", "2026-02"]
    assert respuesta.series[0].etiqueta == "ANA ASESORA"
    assert respuesta.series[0].valores == [100.5, 80]
    assert respuesta.series[1].valores == [0, 20]
    assert respuesta.totales_por_periodo == [100.5, 100]
    assert respuesta.total_general == 200.5
    assert respuesta.resumen.cantidad_movimientos == 4
    assert respuesta.catalogos.agencias == ["MATRIZ"]
