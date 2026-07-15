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
    InputRecuperacionHistoricoRango,
)


MongoDocument = dict[str, Any]
COLECCION_RECUPERACION = "RecuperacionCrediticia"
COLECCION_RECUPERACION_ACTUAL = "RecuperacionCrediticiaActual"
COLECCION_SITUACION = "SituacionCrediticia"
COLECCION_SITUACION_ACTUAL = "SituacionCrediticiaActual"
TAMANO_LOTE_PRESTAMOS = 1_000


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
        estados_inicio: dict[str, str] = {}
        dimensiones: dict[str, dict[str, Any]] = {}
        for lote in _lotes(sorted(numeros_prestamo), TAMANO_LOTE_PRESTAMOS):
            for documento in self._situacion_collection(fecha_inicio, fecha_actual).find(
                self._filtro_situacion(fecha_inicio, fecha_actual, lote),
                {"_id": 0, "NumeroPrestamo": 1, "EstadoPrestamo": 1},
            ):
                numero = _numero_prestamo(documento)
                if numero:
                    estados_inicio.setdefault(numero, _texto(documento.get("EstadoPrestamo")))

            for documento in self._situacion_collection(fecha_fin, fecha_actual).find(
                self._filtro_situacion(fecha_fin, fecha_actual, lote),
                _proyeccion_inicio(),
            ):
                numero = _numero_prestamo(documento)
                if numero:
                    dimensiones.setdefault(numero, documento)

        resultado = {
            numero: _prestamo_desde_situacion(
                numero,
                dimensiones.get(numero),
                estados_inicio.get(numero),
            )
            for numero in numeros_prestamo
        }
        print(
            "[recuperacion][mongo] prestamos "
            f"inicio={fecha_inicio} fin={fecha_fin} unicos={len(numeros_prestamo)} "
            f"inicio_encontrados={len(estados_inicio)} fin_encontrados={len(dimensiones)} "
            f"total_ms={(perf_counter() - inicio_total) * 1000:.2f}"
        )
        return resultado

    def _situacion_collection(self, fecha_corte: str, fecha_actual: str) -> Collection[MongoDocument]:
        return self.situacion_actual_collection if fecha_corte == fecha_actual else self.situacion_collection

    @staticmethod
    def _filtro_situacion(fecha_corte: str, fecha_actual: str, lote: list[str]) -> dict[str, Any]:
        filtro: dict[str, Any] = {"NumeroPrestamo": {"$in": lote}}
        if fecha_corte != fecha_actual:
            filtro["fecha_corte"] = fecha_corte
        return filtro

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
                    "tipo_cobro": "$cobros.tipo_cobro",
                    "valor_recuperado": "$cobros.valor",
                }
            },
            {"$sort": {"fecha_corte": 1, "numero_prestamo": 1, "tipo_transaccion": 1, "tipo_cobro": 1}},
        ]


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
    }


def _lotes(valores: list[str], tamano: int):
    for inicio in range(0, len(valores), tamano):
        yield valores[inicio : inicio + tamano]


def _numero_prestamo(documento: dict[str, Any]) -> str:
    valor = documento.get("NumeroPrestamo")
    return str(valor).strip() if valor is not None else ""


def _texto(valor: Any) -> str:
    return str(valor or "SIN DATOS").strip().upper() or "SIN DATOS"


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
    estado_inicio: str | None,
) -> PrestamoRecuperacion:
    fin = fin or {}
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
        estado_prestamo_inicio=estado_inicio or "SIN DATOS",
        estado_prestamo_fin=_texto(fin.get("EstadoPrestamo")),
    )
