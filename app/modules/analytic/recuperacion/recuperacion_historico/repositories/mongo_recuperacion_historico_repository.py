from datetime import date, datetime, timedelta
from time import perf_counter
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from app.modules.analytic.recuperacion.recuperacion_historico.domain import (
    PrestamoRecuperacion,
    RecuperacionEtiquetada,
)
from app.modules.analytic.recuperacion.recuperacion_historico.schemas import (
    InputRecuperacionHistoricoAgrupado,
    InputRecuperacionHistoricoRango,
)


MongoDocument = dict[str, Any]
COLECCION_RECUPERACION = "RecuperacionCrediticia"
COLECCION_RECUPERACION_ACTUAL = "RecuperacionCrediticiaActual"
COLECCION_SITUACION = "SituacionCrediticia"
COLECCION_SITUACION_ACTUAL = "SituacionCrediticiaActual"
TAMANO_LOTE_PRESTAMOS = 1_000
DIMENSIONES_MOVIMIENTO = {
    "agencia",
    "asesor",
    "tipo_cobro",
    "tipo_transaccion",
    "abogado_externo",
    "nombre_cobranza_apoyo",
    "estado_prestamo_anterior_cobro",
    "calificacion_anterior_cobro",
    "estado_prestamo_actual_cobro",
    "calificacion_actual_cobro",
}
DIMENSIONES_CONTEXTO_INICIAL = {
    "estado_prestamo_anterior_cobro",
    "calificacion_anterior_cobro",
}
def _expresion_numero(campo: str) -> dict[str, Any]:
    return {
        "$convert": {
            "input": campo,
            "to": "double",
            "onError": 0,
            "onNull": 0,
        }
    }


def _cobros() -> list[dict[str, Any]]:
    return [
        {"tipo_cobro": "CAPITAL", "valor": _expresion_numero("$CAPITAL")},
        {"tipo_cobro": "INTERES", "valor": _expresion_numero("$INTERES")},
        {"tipo_cobro": "INTERES_MORA", "valor": _expresion_numero("$INTERES_MORA")},
        {"tipo_cobro": "SEGURO", "valor": _expresion_numero("$SEGURO")},
        {"tipo_cobro": "CASTIGO", "valor": _expresion_numero("$CASTIGO")},
        {"tipo_cobro": "COBRANZA", "valor": _expresion_numero("$COBRANZA")},
        {"tipo_cobro": "JUDICIAL", "valor": _expresion_numero("$JUDICIAL")},
        {"tipo_cobro": "DIFERIDO", "valor": _expresion_numero("$DIFERIDO")},
        {"tipo_cobro": "OTROS", "valor": _expresion_numero("$OTROS")},
    ]


class MongoRecuperacionHistoricoRepository:
    """Lee recuperaciones cerradas y, para hoy, la colección operativa actual."""

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.collection: Collection[MongoDocument] = mongo_db[COLECCION_RECUPERACION]
        self.actual_collection: Collection[MongoDocument] = mongo_db[COLECCION_RECUPERACION_ACTUAL]
        self.situacion_collection: Collection[MongoDocument] = mongo_db[COLECCION_SITUACION]
        self.situacion_actual_collection: Collection[MongoDocument] = mongo_db[
            COLECCION_SITUACION_ACTUAL
        ]

    def obtener_recuperaciones(
        self,
        input_data: InputRecuperacionHistoricoRango,
        fecha_actual: date,
    ) -> list[RecuperacionEtiquetada]:
        fecha_desde = input_data.fecha_desde.strftime("%Y%m%d")
        fecha_hasta = input_data.fecha_hasta.strftime("%Y%m%d")
        fecha_actual_str = fecha_actual.strftime("%Y%m%d")
        fecha_historica_hasta = min(
            fecha_hasta,
            (fecha_actual - timedelta(days=1)).strftime("%Y%m%d"),
        )
        consultas: list[tuple[str, Collection[MongoDocument], list[dict[str, Any]], bool]] = []
        if fecha_desde <= fecha_historica_hasta:
            consultas.append(
                (
                    "historico",
                    self.collection,
                    self._construir_pipeline(fecha_desde, fecha_historica_hasta),
                    False,
                )
            )
        if fecha_desde <= fecha_actual_str <= fecha_hasta:
            consultas.append(
                (
                    "actual",
                    self.actual_collection,
                    self._construir_pipeline(fecha_actual_str, fecha_actual_str),
                    True,
                )
            )
        print(
            "[recuperacion][mongo] inicio "
            f"rango={fecha_desde}:{fecha_hasta} fuentes={','.join(nombre for nombre, *_ in consultas) or 'ninguna'}"
        )
        mapeo_ms = 0.0
        resultado: list[RecuperacionEtiquetada] = []
        cursor_ms = 0.0
        fetch_ms = 0.0
        for nombre, collection, pipeline, es_actual in consultas:
            inicio_cursor = perf_counter()
            filas = collection.aggregate(pipeline, allowDiskUse=True)
            cursor_ms += (perf_counter() - inicio_cursor) * 1000
            inicio_consumo = perf_counter()
            filas_fuente = 0
            mapeo_fuente_ms = 0.0
            for fila in filas:
                inicio_mapeo = perf_counter()
                fecha = datetime.strptime(str(fila["fecha_corte"]), "%Y%m%d").date()
                resultado.append(
                    RecuperacionEtiquetada(
                        fecha_cobro=fecha,
                        numero_prestamo=str(fila.get("numero_prestamo") or ""),
                        tipo_cobro=str(fila["tipo_cobro"]),
                        tipo_transaccion=str(fila.get("tipo_transaccion") or "SIN DATOS"),
                        valor_recuperado=float(fila.get("valor_recuperado") or 0),
                        es_actual=es_actual,
                        agencia=_texto(fila.get("agencia")),
                        asesor=_texto(fila.get("asesor")),
                        abogado_externo=_texto(fila.get("abogado_externo")),
                        codigo_cobranza_apoyo=_texto(fila.get("codigo_cobranza_apoyo")),
                        nombre_cobranza_apoyo=_texto(fila.get("nombre_cobranza_apoyo")),
                        estado_prestamo_cobro=_texto(fila.get("estado_prestamo_cobro")),
                        calificacion_cobro=_texto(fila.get("calificacion_cobro")),
                        fecha_estado_prestamo_anterior_cobro=str(
                            fila.get("fecha_estado_prestamo_anterior_cobro") or ""
                        ),
                        estado_prestamo_anterior_cobro=_texto(
                            fila.get("estado_prestamo_anterior_cobro")
                        ),
                        fecha_estado_prestamo_actual_cobro=str(
                            fila.get("fecha_estado_prestamo_actual_cobro") or ""
                        ),
                        estado_prestamo_actual_cobro=_texto(
                            fila.get("estado_prestamo_actual_cobro")
                        ),
                        calificacion_anterior_cobro=_texto(
                            fila.get("calificacion_anterior_cobro")
                        ),
                        calificacion_actual_cobro=_texto(
                            fila.get("calificacion_actual_cobro")
                        ),
                        es_cancelado_anterior_cobro=_booleano(
                            fila.get("es_cancelado_anterior_cobro")
                        ),
                        es_cancelado_actual_cobro=_booleano(
                            fila.get("es_cancelado_actual_cobro")
                        ),
                        se_cancelo_con_el_cobro=_booleano(
                            fila.get("se_cancelo_con_el_cobro")
                        ),
                    )
                )
                duracion_mapeo_ms = (perf_counter() - inicio_mapeo) * 1000
                mapeo_ms += duracion_mapeo_ms
                mapeo_fuente_ms += duracion_mapeo_ms
                filas_fuente += 1
            fetch_ms += (perf_counter() - inicio_consumo) * 1000 - mapeo_fuente_ms
            print(f"[recuperacion][mongo] fuente={nombre} filas={filas_fuente}")
        resultado.sort(
            key=lambda recuperacion: (
                recuperacion.fecha_cobro,
                recuperacion.numero_prestamo,
                recuperacion.tipo_transaccion,
                recuperacion.tipo_cobro,
            )
        )
        print(
            "[recuperacion][mongo] "
            f"cursor_ms={cursor_ms:.2f} fetch_ms={fetch_ms:.2f} "
            f"mapping_ms={mapeo_ms:.2f} filas={len(resultado)}"
        )
        return resultado

    def obtener_recuperacion_agrupada(
        self,
        input_data: InputRecuperacionHistoricoAgrupado,
        fecha_actual: date,
    ) -> dict[str, Any]:
        """Agrupa en MongoDB y solo materializa series y catálogos pequeños."""
        fecha_desde = input_data.fecha_desde.strftime("%Y%m%d")
        fecha_hasta = input_data.fecha_hasta.strftime("%Y%m%d")
        fecha_actual_str = fecha_actual.strftime("%Y%m%d")
        fecha_historica_hasta = min(
            fecha_hasta,
            (fecha_actual - timedelta(days=1)).strftime("%Y%m%d"),
        )
        consultas: list[tuple[str, Collection[MongoDocument], str, str]] = []
        if fecha_desde <= fecha_historica_hasta:
            consultas.append(
                ("historico", self.collection, fecha_desde, fecha_historica_hasta)
            )
        if fecha_desde <= fecha_actual_str <= fecha_hasta:
            consultas.append(
                ("actual", self.actual_collection, fecha_actual_str, fecha_actual_str)
            )

        datos: dict[tuple[str, str], dict[str, Any]] = {}
        agencias: set[str] = set()
        asesores: set[str] = set()
        tipos_prestamo: set[str] = set()
        inicio_total = perf_counter()
        for nombre, collection, desde, hasta in consultas:
            pipeline = self._construir_pipeline_agrupado(
                input_data,
                desde,
                hasta,
                fecha_actual_str,
            )
            inicio_fuente = perf_counter()
            documento = next(iter(collection.aggregate(pipeline, allowDiskUse=True)), None) or {}
            for fila in documento.get("datos", []):
                clave = (str(fila["periodo"]), str(fila["etiqueta"]))
                acumulado = datos.setdefault(
                    clave,
                    {
                        "periodo": clave[0],
                        "etiqueta": clave[1],
                        "valor": 0.0,
                        "cantidad_movimientos": 0,
                    },
                )
                acumulado["valor"] += float(fila.get("valor") or 0)
                acumulado["cantidad_movimientos"] += int(
                    fila.get("cantidad_movimientos") or 0
                )
            agencias.update(_catalogo_desde_facet(documento.get("agencias", [])))
            asesores.update(_catalogo_desde_facet(documento.get("asesores", [])))
            tipos_prestamo.update(
                _catalogo_desde_facet(documento.get("tipos_prestamo", []))
            )
            print(
                "[recuperacion][mongo][agrupado] "
                f"fuente={nombre} filas={len(documento.get('datos', []))} "
                f"total_ms={(perf_counter() - inicio_fuente) * 1000:.2f}"
            )

        print(
            "[recuperacion][mongo][agrupado] "
            f"dimension={input_data.dimension} filas_finales={len(datos)} "
            f"total_ms={(perf_counter() - inicio_total) * 1000:.2f}"
        )
        return {
            "datos": list(datos.values()),
            "agencias": sorted(agencias),
            "asesores": sorted(asesores),
            "tipos_prestamo": sorted(tipos_prestamo),
        }

    def obtener_prestamos_por_numero(
        self,
        numeros_prestamo: set[str],
        fecha_inicio: str,
        fecha_fin: str,
        fecha_actual: str,
    ) -> dict[str, PrestamoRecuperacion]:
        """Obtiene las dimensiones del corte final y los estados del rango."""
        if not numeros_prestamo:
            return {}

        inicio_total = perf_counter()
        situaciones_inicio: dict[str, dict[str, Any]] = {}
        dimensiones: dict[str, dict[str, Any]] = {}
        for lote in _lotes(sorted(numeros_prestamo), TAMANO_LOTE_PRESTAMOS):
            for documento in self._obtener_situaciones_con_fallback_actual(
                fecha_inicio,
                fecha_actual,
                lote,
                {"_id": 0, "NumeroPrestamo": 1, "EstadoPrestamo": 1, "Calificacion": 1},
            ):
                numero = _numero_prestamo(documento)
                if numero:
                    situaciones_inicio.setdefault(numero, documento)

            for documento in self._obtener_situaciones_con_fallback_actual(
                fecha_fin,
                fecha_actual,
                lote,
                _proyeccion_inicio(),
            ):
                numero = _numero_prestamo(documento)
                if numero:
                    dimensiones.setdefault(numero, documento)

        resultado = {
            numero: _prestamo_desde_situacion(
                numero,
                dimensiones.get(numero),
                situaciones_inicio.get(numero),
            )
            for numero in numeros_prestamo
        }
        print(
            "[recuperacion][mongo] prestamos "
            f"inicio={fecha_inicio} fin={fecha_fin} unicos={len(numeros_prestamo)} "
            f"inicio_encontrados={len(situaciones_inicio)} fin_encontrados={len(dimensiones)} "
            f"total_ms={(perf_counter() - inicio_total) * 1000:.2f}"
        )
        return resultado

    def _obtener_situaciones_con_fallback_actual(
        self,
        fecha_corte: str,
        fecha_actual: str,
        lote: list[str],
        projection: dict[str, int],
    ) -> list[MongoDocument]:
        """Consulta el corte solicitado y, si es hoy, completa faltantes con ayer."""
        if fecha_corte != fecha_actual:
            return list(
                self.situacion_collection.find(
                    {
                        "NumeroPrestamo": {"$in": lote},
                        "fecha_corte": fecha_corte,
                    },
                    projection,
                )
            )

        documentos = list(
            self.situacion_actual_collection.find(
                {"NumeroPrestamo": {"$in": lote}},
                projection,
            )
        )
        encontrados = {
            numero
            for documento in documentos
            if (numero := _numero_prestamo(documento))
        }
        faltantes = [numero for numero in lote if numero not in encontrados]
        if not faltantes:
            return documentos

        fecha_anterior = _fecha_anterior(fecha_actual)
        documentos.extend(
            list(
                self.situacion_collection.find(
                    {
                        "NumeroPrestamo": {"$in": faltantes},
                        "fecha_corte": fecha_anterior,
                    },
                    projection,
                )
            )
        )
        return documentos

    @staticmethod
    def _construir_pipeline(fecha_desde: str, fecha_hasta: str) -> list[dict[str, Any]]:
        return [
            {"$match": {"fecha_corte": {"$gte": fecha_desde, "$lte": fecha_hasta}}},
            {
                "$project": {
                    "fecha_corte": 1,
                    "numero_prestamo": {"$ifNull": ["$NUMERO_PRESTAMO", "$NumeroPrestamo"]},
                    "tipo_transaccion": {"$ifNull": ["$TIPO_TRANSACCION", "$TipoTransaccion"]},
                    "agencia": "$AGENCIA",
                    "asesor": {"$ifNull": ["$NOMBRE_ASESOR_COBRO", "$CODIGO_ASESOR_COBRO"]},
                    "abogado_externo": "$ABOGADO_EXTERNO_COBRO",
                    "codigo_cobranza_apoyo": "$CODIGO_COBRANZA_APOYO_COBRO",
                    "nombre_cobranza_apoyo": "$NOMBRE_COBRANZA_APOYO_COBRO",
                    "estado_prestamo_cobro": "$ESTADO_PRESTAMO_COBRO",
                    "calificacion_cobro": "$CALIFICACION_COBRO",
                    "fecha_estado_prestamo_anterior_cobro": {
                        "$ifNull": ["$FECHA_ESTADO_PRESTAMO_ANTERIOR_COBRO", ""]
                    },
                    "estado_prestamo_anterior_cobro": "$ESTADO_PRESTAMO_ANTERIOR_COBRO",
                    "fecha_estado_prestamo_actual_cobro": {
                        "$ifNull": ["$FECHA_ESTADO_PRESTAMO_ACTUAL_COBRO", "$fecha_corte"]
                    },
                    "estado_prestamo_actual_cobro": {
                        "$ifNull": ["$ESTADO_PRESTAMO_ACTUAL_COBRO", "$ESTADO_PRESTAMO_COBRO"]
                    },
                    "calificacion_anterior_cobro": "$CALIFICACION_ANTERIOR_COBRO",
                    "calificacion_actual_cobro": {
                        "$ifNull": ["$CALIFICACION_ACTUAL_COBRO", "$CALIFICACION_COBRO"]
                    },
                    "es_cancelado_anterior_cobro": {
                        "$ifNull": ["$ES_CANCELADO_ANTERIOR_COBRO", False]
                    },
                    "es_cancelado_actual_cobro": {
                        "$ifNull": ["$ES_CANCELADO_ACTUAL_COBRO", False]
                    },
                    "se_cancelo_con_el_cobro": {
                        "$ifNull": ["$SE_CANCELO_CON_EL_COBRO", False]
                    },
                    "cobros": _cobros(),
                }
            },
            {"$unwind": "$cobros"},
            {"$match": {"cobros.valor": {"$ne": 0}}},
            {
                "$project": {
                    "_id": 0,
                    "fecha_corte": 1,
                    "numero_prestamo": 1,
                    "tipo_transaccion": 1,
                    "agencia": 1,
                    "asesor": 1,
                    "abogado_externo": 1,
                    "codigo_cobranza_apoyo": 1,
                    "nombre_cobranza_apoyo": 1,
                    "estado_prestamo_cobro": 1,
                    "calificacion_cobro": 1,
                    "fecha_estado_prestamo_anterior_cobro": 1,
                    "estado_prestamo_anterior_cobro": 1,
                    "fecha_estado_prestamo_actual_cobro": 1,
                    "estado_prestamo_actual_cobro": 1,
                    "calificacion_anterior_cobro": 1,
                    "calificacion_actual_cobro": 1,
                    "es_cancelado_anterior_cobro": 1,
                    "es_cancelado_actual_cobro": 1,
                    "se_cancelo_con_el_cobro": 1,
                    "tipo_cobro": "$cobros.tipo_cobro",
                    "valor_recuperado": "$cobros.valor",
                }
            },
            {"$sort": {"fecha_corte": 1, "numero_prestamo": 1, "tipo_transaccion": 1, "tipo_cobro": 1}},
        ]

    @staticmethod
    def _construir_pipeline_agrupado(
        input_data: InputRecuperacionHistoricoAgrupado,
        fecha_desde: str,
        fecha_hasta: str,
        fecha_actual: str,
    ) -> list[dict[str, Any]]:
        dimension = input_data.dimension
        dimension_movimiento = _dimension_movimiento_origen(dimension)
        group_id: dict[str, Any] = {
            "periodo": "$periodo",
            "numero": "$numero_prestamo",
            "agencia": "$agencia",
            "asesor": "$asesor",
        }
        if dimension_movimiento is not None and dimension not in {"agencia", "asesor"}:
            group_id["dimension"] = dimension_movimiento
        group_id_consolidado: dict[str, Any] = {
            "numero": "$_id.numero",
            "agencia": "$_id.agencia",
            "asesor": "$_id.asesor",
        }
        if "dimension" in group_id:
            group_id_consolidado["dimension"] = "$_id.dimension"

        pipeline: list[dict[str, Any]] = [
            {"$match": {"fecha_corte": {"$gte": fecha_desde, "$lte": fecha_hasta}}},
            {
                "$project": {
                    "periodo": {"$substrBytes": ["$fecha_corte", 0, 6]},
                    "numero_prestamo": {
                        "$trim": {
                            "input": {
                                "$convert": {
                                    "input": {
                                        "$ifNull": ["$NUMERO_PRESTAMO", "$NumeroPrestamo"]
                                    },
                                    "to": "string",
                                    "onError": "",
                                    "onNull": "",
                                }
                            }
                        }
                    },
                    "tipo_transaccion": {
                        "$ifNull": ["$TIPO_TRANSACCION", "$TipoTransaccion"]
                    },
                    "agencia": "$AGENCIA",
                    "asesor": {
                        "$ifNull": ["$NOMBRE_ASESOR_COBRO", "$CODIGO_ASESOR_COBRO"]
                    },
                    "abogado_externo": "$ABOGADO_EXTERNO_COBRO",
                    "nombre_cobranza_apoyo": "$NOMBRE_COBRANZA_APOYO_COBRO",
                    "estado_prestamo_anterior_cobro": "$ESTADO_PRESTAMO_ANTERIOR_COBRO",
                    "calificacion_anterior_cobro": "$CALIFICACION_ANTERIOR_COBRO",
                    "estado_prestamo_actual_cobro": {
                        "$ifNull": [
                            "$ESTADO_PRESTAMO_ACTUAL_COBRO",
                            "$ESTADO_PRESTAMO_COBRO",
                        ]
                    },
                    "calificacion_actual_cobro": {
                        "$ifNull": ["$CALIFICACION_ACTUAL_COBRO", "$CALIFICACION_COBRO"]
                    },
                    "cobros": _cobros(),
                }
            },
            {"$unwind": "$cobros"},
            {"$match": {"cobros.valor": {"$ne": 0}, "numero_prestamo": {"$ne": ""}}},
            {
                "$group": {
                    "_id": group_id,
                    "valor": {"$sum": "$cobros.valor"},
                    "cantidad_movimientos": {"$sum": 1},
                }
            },
            {
                "$group": {
                    "_id": group_id_consolidado,
                    "periodos": {
                        "$push": {
                            "periodo": "$_id.periodo",
                            "valor": "$valor",
                            "cantidad_movimientos": "$cantidad_movimientos",
                        }
                    },
                }
            },
        ]
        pipeline.extend(
            _lookup_corte(
                alias="prestamo_fin",
                fecha_corte=input_data.fecha_hasta.strftime("%Y%m%d"),
                fecha_actual=fecha_actual,
                projection=_proyeccion_inicio(),
            )
        )
        if dimension in DIMENSIONES_CONTEXTO_INICIAL:
            pipeline.extend(
                _lookup_corte(
                    alias="prestamo_inicio",
                    fecha_corte=input_data.fecha_desde.strftime("%Y%m%d"),
                    fecha_actual=fecha_actual,
                    projection={
                        "_id": 0,
                        "NumeroPrestamo": 1,
                        "EstadoPrestamo": 1,
                        "Calificacion": 1,
                    },
                )
            )

        agencia = _contexto_mongo("$_id.agencia", "$prestamo_fin.Agencia")
        asesor = _contexto_mongo(
            "$_id.asesor",
            {"$ifNull": ["$prestamo_fin.NombreAsesor", "$prestamo_fin.CodigoAsesor"]},
        )
        tipo_prestamo = _texto_mongo("$prestamo_fin.TipoPrestamo")
        pipeline.extend(
            [
                {
                    "$project": {
                        "_id": 0,
                        "numero_prestamo": "$_id.numero",
                        "periodos": 1,
                        "agencia": agencia,
                        "asesor": asesor,
                        "tipo_prestamo": tipo_prestamo,
                        "dimension": _dimension_agrupada(
                            dimension,
                            agencia=agencia,
                            asesor=asesor,
                            tipo_prestamo=tipo_prestamo,
                        ),
                    }
                },
                {
                    "$facet": {
                        "datos": [
                            *_filtros_pipeline(input_data, incluir_tipo=True),
                            {"$unwind": "$periodos"},
                            {
                                "$group": {
                                    "_id": {
                                        "periodo": "$periodos.periodo",
                                        "etiqueta": "$dimension",
                                    },
                                    "valor": {"$sum": "$periodos.valor"},
                                    "cantidad_movimientos": {
                                        "$sum": "$periodos.cantidad_movimientos"
                                    },
                                }
                            },
                            {
                                "$project": {
                                    "_id": 0,
                                    "periodo": "$_id.periodo",
                                    "etiqueta": "$_id.etiqueta",
                                    "valor": 1,
                                    "cantidad_movimientos": 1,
                                }
                            },
                            {"$sort": {"periodo": 1, "etiqueta": 1}},
                        ],
                        "agencias": _pipeline_catalogo("agencia"),
                        "asesores": [
                            *_match_lista("agencia", input_data.agencias),
                            *_pipeline_catalogo("asesor"),
                        ],
                        "tipos_prestamo": [
                            *_match_lista("agencia", input_data.agencias),
                            *_match_lista("asesor", input_data.asesores),
                            *_pipeline_catalogo("tipo_prestamo"),
                        ],
                    }
                },
            ]
        )
        return pipeline

def _proyeccion_inicio() -> dict[str, int]:
    return {
        "_id": 0,
        "NumeroPrestamo": 1,
        "Agencia": 1,
        "TipoCondicion": 1,
        "TipoPrestamo": 1,
        "Producto": 1,
        "Segmento": 1,
        "NombreAsesor": 1,
        "CodigoAsesor": 1,
        "Provincia": 1,
        "Canton": 1,
        "Parroquia": 1,
        "Educacion": 1,
        "Educación": 1,
        "NivelEducacion": 1,
        "NivelDeEducacion": 1,
        "Edad": 1,
        "TipoDeGarantia": 1,
        "TipoGarantia": 1,
        "GarantiaTipo": 1,
        "DeudaInicial": 1,
        "TasaNominal": 1,
        "TasaAnual": 1,
        "Plazo": 1,
        "EstadoPrestamo": 1,
        "Calificacion": 1,
    }


def _lotes(valores: list[str], tamano: int):
    for inicio in range(0, len(valores), tamano):
        yield valores[inicio : inicio + tamano]


def _numero_prestamo(documento: dict[str, Any]) -> str:
    valor = documento.get("NumeroPrestamo")
    return str(valor).strip() if valor is not None else ""


def _fecha_anterior(fecha_corte: str) -> str:
    return (datetime.strptime(fecha_corte, "%Y%m%d").date() - timedelta(days=1)).strftime("%Y%m%d")


def _texto(valor: Any) -> str:
    return str(valor or "SIN DATOS").strip().upper() or "SIN DATOS"


def _booleano(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    return str(valor or "").strip().upper() in {"1", "TRUE", "SI", "SÍ"}


def _valor_numerico(valor: Any, *, entero: bool = False) -> float | int | None:
    if isinstance(valor, bool):
        return None
    try:
        convertido = float(valor)
    except (TypeError, ValueError):
        return None
    if convertido < 0:
        return None
    return int(convertido) if entero else convertido


def _prestamo_desde_situacion(
    numero_prestamo: str,
    fin: dict[str, Any] | None,
    inicio: dict[str, Any] | None,
) -> PrestamoRecuperacion:
    fin = fin or {}
    inicio = inicio or {}
    return PrestamoRecuperacion(
        numero_prestamo=numero_prestamo,
        agencia=_texto(fin.get("Agencia")),
        condicion=_texto(fin.get("TipoCondicion")),
        tipo_prestamo=_texto(fin.get("TipoPrestamo")),
        producto=_texto(fin.get("Producto")),
        segmento=_texto(fin.get("Segmento")),
        asesor=_texto(fin.get("NombreAsesor") or fin.get("CodigoAsesor")),
        provincia=_texto(fin.get("Provincia")),
        canton=_texto(fin.get("Canton")),
        parroquia=_texto(fin.get("Parroquia")),
        educacion=_texto(
            fin.get("Educacion")
            or fin.get("Educación")
            or fin.get("NivelEducacion")
            or fin.get("NivelDeEducacion")
        ),
        edad=_valor_numerico(fin.get("Edad"), entero=True), # type: ignore
        garantia=_texto(
            fin.get("TipoDeGarantia")
            or fin.get("TipoGarantia")
            or fin.get("GarantiaTipo")
        ),
        monto=_valor_numerico(fin.get("DeudaInicial")),
        tasa=_valor_numerico(fin.get("TasaNominal")),
        tasa_real=_valor_numerico(fin.get("TasaAnual")),
        plazo=_valor_numerico(fin.get("Plazo"), entero=True), # type: ignore
        estado_prestamo_inicio=_texto(inicio.get("EstadoPrestamo")),
        estado_prestamo_fin=_texto(fin.get("EstadoPrestamo")),
        calificacion_inicio=_texto(inicio.get("Calificacion")),
        calificacion_fin=_texto(fin.get("Calificacion")),
    )


def _catalogo_desde_facet(filas: list[dict[str, Any]]) -> set[str]:
    return {
        str(fila.get("valor") or "").strip()
        for fila in filas
        if str(fila.get("valor") or "").strip()
    }


def _dimension_movimiento_origen(dimension: str) -> Any | None:
    if dimension not in DIMENSIONES_MOVIMIENTO:
        return None
    if dimension == "tipo_cobro":
        return "$cobros.tipo_cobro"
    return f"${dimension}"


def _lookup_corte(
    *,
    alias: str,
    fecha_corte: str,
    fecha_actual: str,
    projection: dict[str, int],
) -> list[dict[str, Any]]:
    if fecha_corte != fecha_actual:
        historico = f"{alias}_historico"
        return [
            _lookup_historico(historico, fecha_corte, projection),
            {
                "$set": {
                    alias: {
                        "$ifNull": [
                            {"$arrayElemAt": [f"${historico}", 0]},
                            {},
                        ]
                    }
                }
            },
        ]

    actual = f"{alias}_actual"
    historico = f"{alias}_historico"
    fecha_anterior = _fecha_anterior(fecha_actual)
    return [
        {
            "$lookup": {
                "from": COLECCION_SITUACION_ACTUAL,
                "let": {"numero": "$_id.numero"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {"$eq": ["$NumeroPrestamo", "$$numero"]}
                        }
                    },
                    {"$project": projection},
                    {"$limit": 1},
                ],
                "as": actual,
            }
        },
        _lookup_historico(historico, fecha_anterior, projection),
        {
            "$set": {
                alias: {
                    "$ifNull": [
                        {"$arrayElemAt": [f"${actual}", 0]},
                        {
                            "$ifNull": [
                                {"$arrayElemAt": [f"${historico}", 0]},
                                {},
                            ]
                        },
                    ]
                }
            }
        },
    ]


def _lookup_historico(
    alias: str,
    fecha_corte: str,
    projection: dict[str, int],
) -> dict[str, Any]:
    return {
        "$lookup": {
            "from": COLECCION_SITUACION,
            "let": {"numero": "$_id.numero"},
            "pipeline": [
                {
                    "$match": {
                        "fecha_corte": fecha_corte,
                        "$expr": {"$eq": ["$NumeroPrestamo", "$$numero"]},
                    }
                },
                {"$project": projection},
                {"$limit": 1},
            ],
            "as": alias,
        }
    }


def _texto_mongo(valor: Any) -> dict[str, Any]:
    texto = {
        "$trim": {
            "input": {
                "$convert": {
                    "input": valor,
                    "to": "string",
                    "onError": "",
                    "onNull": "",
                }
            }
        }
    }
    return {
        "$let": {
            "vars": {"texto": texto},
            "in": {
                "$cond": [
                    {"$eq": ["$$texto", ""]},
                    "SIN DATOS",
                    {"$toUpper": "$$texto"},
                ]
            },
        }
    }


def _contexto_mongo(valor: Any, respaldo: Any) -> dict[str, Any]:
    return {
        "$let": {
            "vars": {"valor": _texto_mongo(valor)},
            "in": {
                "$cond": [
                    {"$eq": ["$$valor", "SIN DATOS"]},
                    _texto_mongo(respaldo),
                    "$$valor",
                ]
            },
        }
    }


def _dimension_agrupada(
    dimension: str,
    *,
    agencia: Any,
    asesor: Any,
    tipo_prestamo: Any,
) -> Any:
    if dimension == "agencia":
        return agencia
    if dimension == "asesor":
        return asesor
    if dimension == "tipo_prestamo":
        return tipo_prestamo

    campos_prestamo = {
        "condicion": "$prestamo_fin.TipoCondicion",
        "producto": "$prestamo_fin.Producto",
        "segmento": "$prestamo_fin.Segmento",
        "provincia": "$prestamo_fin.Provincia",
        "canton": "$prestamo_fin.Canton",
        "parroquia": "$prestamo_fin.Parroquia",
        "educacion": {
            "$ifNull": [
                "$prestamo_fin.Educacion",
                {
                    "$ifNull": [
                        "$prestamo_fin.Educación",
                        {
                            "$ifNull": [
                                "$prestamo_fin.NivelEducacion",
                                "$prestamo_fin.NivelDeEducacion",
                            ]
                        },
                    ]
                },
            ]
        },
        "garantia": {
            "$ifNull": [
                "$prestamo_fin.TipoDeGarantia",
                {
                    "$ifNull": [
                        "$prestamo_fin.TipoGarantia",
                        "$prestamo_fin.GarantiaTipo",
                    ]
                },
            ]
        },
    }
    if dimension in campos_prestamo:
        return _texto_mongo(campos_prestamo[dimension])
    if dimension == "edad":
        return _rango_mongo(
            "$prestamo_fin.Edad",
            [9, 19, 29, 39, 49, 59, 69, 79, 89],
            [
                "0-9",
                "10-19",
                "20-29",
                "30-39",
                "40-49",
                "50-59",
                "60-69",
                "70-79",
                "80-89",
                "90+",
            ],
        )
    if dimension == "monto":
        return _rango_mongo(
            "$prestamo_fin.DeudaInicial",
            [3000, 5000, 8000, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000],
            [
                "Hasta 3.000",
                "Hasta 5.000",
                "Hasta 8.000",
                "Hasta 10.000",
                "Hasta 20.000",
                "Hasta 30.000",
                "Hasta 40.000",
                "Hasta 50.000",
                "Hasta 60.000",
                "Hasta 70.000",
                "Hasta 80.000",
                "Hasta 90.000",
                "Hasta 100.000",
                "Más de 100.000",
            ],
        )
    if dimension in {"tasa", "tasa_real"}:
        campo = "$prestamo_fin.TasaNominal" if dimension == "tasa" else "$prestamo_fin.TasaAnual"
        return _rango_mongo(
            campo,
            [13, 14, 16, 17, 18, 19, 20, 21],
            [
                "Hasta 13%",
                "Hasta 14%",
                "Hasta 16%",
                "Hasta 17%",
                "Hasta 18%",
                "Hasta 19%",
                "Hasta 20%",
                "Hasta 21%",
                "Más de 22%",
            ],
        )
    if dimension == "plazo":
        return _rango_mongo(
            "$prestamo_fin.Plazo",
            [12, 24, 36, 48, 60, 72, 84, 96, 120],
            [
                "Hasta 1 AÑO",
                "Hasta 2 AÑOS",
                "Hasta 3 AÑOS",
                "Hasta 4 AÑOS",
                "Hasta 5 AÑOS",
                "Hasta 6 AÑOS",
                "Hasta 7 AÑOS",
                "Hasta 8 AÑOS",
                "Hasta 10 AÑOS",
                "Más de 10 AÑOS",
            ],
        )

    if dimension == "estado_prestamo_anterior_cobro":
        return _contexto_mongo("$_id.dimension", "$prestamo_inicio.EstadoPrestamo")
    if dimension == "calificacion_anterior_cobro":
        return _contexto_mongo("$_id.dimension", "$prestamo_inicio.Calificacion")
    if dimension == "estado_prestamo_actual_cobro":
        return _contexto_mongo("$_id.dimension", "$prestamo_fin.EstadoPrestamo")
    if dimension == "calificacion_actual_cobro":
        return _contexto_mongo("$_id.dimension", "$prestamo_fin.Calificacion")
    return _texto_mongo("$_id.dimension")


def _rango_mongo(
    campo: Any,
    limites: list[int],
    etiquetas: list[str],
) -> dict[str, Any]:
    numero = {
        "$convert": {
            "input": campo,
            "to": "double",
            "onError": None,
            "onNull": None,
        }
    }
    return {
        "$let": {
            "vars": {"numero": numero},
            "in": {
                "$cond": [
                    {
                        "$or": [
                            {"$eq": ["$$numero", None]},
                            {"$lt": ["$$numero", 0]},
                        ]
                    },
                    "SIN DATOS",
                    {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {"$lte": ["$$numero", limite]},
                                    "then": etiquetas[indice],
                                }
                                for indice, limite in enumerate(limites)
                            ],
                            "default": etiquetas[-1],
                        }
                    },
                ]
            },
        }
    }


def _match_lista(campo: str, valores: list[str]) -> list[dict[str, Any]]:
    return [{"$match": {campo: {"$in": valores}}}] if valores else []


def _filtros_pipeline(
    input_data: InputRecuperacionHistoricoAgrupado,
    *,
    incluir_tipo: bool,
) -> list[dict[str, Any]]:
    pipeline = [
        *_match_lista("agencia", input_data.agencias),
        *_match_lista("asesor", input_data.asesores),
    ]
    if incluir_tipo:
        pipeline.extend(_match_lista("tipo_prestamo", input_data.tipos_prestamo))
    return pipeline


def _pipeline_catalogo(campo: str) -> list[dict[str, Any]]:
    return [
        {"$group": {"_id": f"${campo}"}},
        {"$project": {"_id": 0, "valor": "$_id"}},
        {"$sort": {"valor": 1}},
    ]
