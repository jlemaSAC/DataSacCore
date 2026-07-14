from typing import Any
from time import perf_counter

from pymongo.collection import Collection
from pymongo.database import Database

from app.modules.analytic.recuperacion.recuperacion_historico.domain import RecuperacionAgrupada
from app.modules.analytic.recuperacion.recuperacion_historico.schemas import (
    InputRecuperacionHistoricoRango,
)


MongoDocument = dict[str, Any]
COLECCION_RECUPERACION = "RecuperacionCrediticia"
COLECCION_SITUACION = "SituacionCrediticia"

TEXTO_CAMPOS = {
    "estado_prestamo_inicio",
    "estado_prestamo_fin",
    "tipo_cobro",
    "tipo_transaccion",
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
}
NUMERO_CAMPOS = {"tasa_valor", "tasa_real_valor", "plazo_valor"}


def _numero(campo: str) -> dict[str, Any]:
    return {
        "$convert": {
            "input": campo,
            "to": "double",
            "onError": None,
            "onNull": None,
        }
    }


def _rango_numerico(
    campo: str,
    rangos: tuple[tuple[int, str], ...],
    mayor: str,
) -> dict[str, Any]:
    valor = _numero(campo)
    return {
        "$switch": {
            "branches": [
                {
                    "case": {"$or": [{"$eq": [valor, None]}, {"$lt": [valor, 0]}]},
                    "then": "SIN DATOS",
                },
                *[
                    {"case": {"$lte": [valor, limite]}, "then": etiqueta}
                    for limite, etiqueta in rangos
                ],
            ],
            "default": mayor,
        }
    }


def _texto(campo: str, respaldo: str | None = None) -> dict[str, Any]:
    valor: Any = campo
    if respaldo:
        valor = {"$ifNull": [campo, respaldo]}
    return {"$ifNull": [valor, "SIN DATOS"]}


CAMPO_GRUPO: dict[str, Any] = {
    "tipo_cobro": "$cobros.tipo_cobro",
    "tipo_transaccion": _texto("$tipo_transaccion"),
    "estado_prestamo_inicio": _texto("$situacion_inicio.EstadoPrestamo"),
    "estado_prestamo_fin": _texto("$situacion_fin.EstadoPrestamo"),
    "agencia": _texto("$situacion.Agencia"),
    "condicion": _texto("$situacion.TipoCondicion"),
    "tipo_prestamo": _texto("$situacion.TipoPrestamo"),
    "producto": _texto("$situacion.Producto"),
    "segmento": _texto("$situacion.Segmento"),
    "asesor": _texto("$situacion.NombreAsesor", "$situacion.CodigoAsesor"),
    "provincia": _texto("$situacion.Provincia"),
    "canton": _texto("$situacion.Canton"),
    "parroquia": _texto("$situacion.Parroquia"),
    "educacion": _texto("$situacion.Educacion"),
    "edad": _rango_numerico(
        "$situacion.Edad",
        ((20, "HASTA 20"), (30, "HASTA 30"), (40, "HASTA 40"), (50, "HASTA 50"),
         (60, "HASTA 60"), (70, "HASTA 70"), (80, "HASTA 80"), (90, "HASTA 90"),
         (100, "HASTA 100")),
        "MAS DE 100",
    ),
    "garantia": _texto("$situacion.TipoDeGarantia"),
    "monto": _rango_numerico(
        "$situacion.DeudaInicial",
        ((3000, "A.Hasta 3.000"), (5000, "B.Hasta 5.000"), (8000, "C.Hasta 8.000"),
         (10000, "D.Hasta 10.000"), (20000, "E.Hasta 20.000"), (30000, "F.Hasta 30.000"),
         (40000, "G.Hasta 40.000"), (50000, "H.Hasta 50.000"), (60000, "I.Hasta 60.000"),
         (70000, "J.Hasta 70.000"), (80000, "K.Hasta 80.000"), (90000, "L.Hasta 90.000"),
         (100000, "M.Hasta 100.000")),
        "N.Mas de 100.000",
    ),
    "tasa": _rango_numerico(
        "$situacion.TasaNominal",
        ((13, "D.Hasta 13"), (14, "E.Hasta 14"), (16, "G.Hasta 16"), (17, "H.Hasta 17"),
         (18, "I.Hasta 18"), (19, "J.Hasta 19"), (20, "K.Hasta 20"), (21, "L.Hasta 21")),
        "N.Mas de 22",
    ),
    "tasa_valor": _numero("$situacion.TasaNominal"),
    "tasa_real": _rango_numerico(
        "$situacion.TasaAnual",
        ((13, "D.Hasta 13"), (14, "E.Hasta 14"), (16, "G.Hasta 16"), (17, "H.Hasta 17"),
         (18, "I.Hasta 18"), (19, "J.Hasta 19"), (20, "K.Hasta 20"), (21, "L.Hasta 21")),
        "N.Mas de 22",
    ),
    "tasa_real_valor": _numero("$situacion.TasaAnual"),
    "plazo": _rango_numerico(
        "$situacion.Plazo",
        ((12, "A.Hasta 1 AÑO"), (24, "B.Hasta 2 AÑOS"), (36, "C.Hasta 3 AÑOS"),
         (48, "D.Hasta 4 AÑOS"), (60, "E.Hasta 5 AÑOS"), (72, "F.Hasta 6 AÑOS"),
         (84, "G.Hasta 7 AÑOS"), (96, "H.Hasta 8 AÑOS"), (120, "J.Hasta 10 AÑOS")),
        "K.Mas de 10 AÑOS",
    ),
    "plazo_valor": _numero("$situacion.Plazo"),
}
TODOS_LOS_CAMPOS = tuple(CAMPO_GRUPO)


def _cobros() -> list[dict[str, Any]]:
    return [
        {"tipo_cobro": "CAPITAL", "valor": _numero("$CAPITAL")},
        {"tipo_cobro": "INTERES", "valor": _numero("$INTERES")},
        {"tipo_cobro": "INTERES_MORA", "valor": _numero("$INTERES_MORA")},
        {"tipo_cobro": "SEGURO", "valor": _numero("$SEGURO")},
        {"tipo_cobro": "CASTIGO", "valor": _numero("$CASTIGO")},
        {"tipo_cobro": "COBRANZA", "valor": _numero("$COBRANZA")},
        {"tipo_cobro": "JUDICIAL", "valor": _numero("$JUDICIAL")},
        {"tipo_cobro": "DIFERIDO", "valor": _numero("$DIFERIDO")},
        {"tipo_cobro": "OTROS", "valor": _numero("$OTROS")},
    ]


class MongoRecuperacionHistoricoRepository:
    """Consulta exclusivamente RecuperacionCrediticia y SituacionCrediticia."""

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.collection: Collection[MongoDocument] = mongo_db[COLECCION_RECUPERACION]

    def obtener_recuperaciones_agrupadas(
        self,
        input_data: InputRecuperacionHistoricoRango,
    ) -> list[RecuperacionAgrupada]:
        fecha_desde = input_data.fecha_desde.strftime("%Y%m%d")
        fecha_hasta = input_data.fecha_hasta.strftime("%Y%m%d")
        inicio_pipeline = perf_counter()
        pipeline = self._construir_pipeline(fecha_desde, fecha_hasta)
        pipeline_ms = (perf_counter() - inicio_pipeline) * 1000
        print(
            "[recuperacion][mongo] inicio "
            f"rango={fecha_desde}:{fecha_hasta} etapas={len(pipeline)} "
            f"pipeline_ms={pipeline_ms:.2f}"
        )

        inicio_cursor = perf_counter()
        filas = self.collection.aggregate(pipeline, allowDiskUse=True)
        cursor_ms = (perf_counter() - inicio_cursor) * 1000

        inicio_consumo = perf_counter()
        mapeo_ms = 0.0
        resultado: list[RecuperacionAgrupada] = []
        for fila in filas:
            inicio_mapeo = perf_counter()
            identificador = fila.get("_id") or {}
            periodo = str(identificador.get("periodo") or "")
            if len(periodo) != 7:
                continue
            dimensiones = {
                campo: self._valor_dimension(identificador.get(campo), campo)
                for campo in CAMPO_GRUPO
            }
            resultado.append(
                RecuperacionAgrupada(
                    periodo=periodo,
                    anio=int(identificador.get("anio") or periodo[:4]),
                    mes=int(identificador.get("mes") or periodo[5:]),
                    dimensiones=dimensiones,
                    total_recuperado=float(fila.get("total_recuperado") or 0),
                )
            )
            mapeo_ms += (perf_counter() - inicio_mapeo) * 1000
        consumo_ms = (perf_counter() - inicio_consumo) * 1000
        print(
            "[recuperacion][mongo] "
            f"pipeline_ms={pipeline_ms:.2f} cursor_ms={cursor_ms:.2f} "
            f"fetch_ms={consumo_ms - mapeo_ms:.2f} mapping_ms={mapeo_ms:.2f} "
            f"filas={len(resultado)} rango={fecha_desde}:{fecha_hasta}"
        )
        return resultado

    @staticmethod
    def _valor_dimension(valor: Any, campo: str) -> Any:
        if campo in NUMERO_CAMPOS:
            return float(valor) if isinstance(valor, int | float) else None
        return str(valor or "SIN DATOS").strip().upper() or "SIN DATOS"

    @staticmethod
    def _lookup_situacion(
        nombre: str,
        fecha: str,
        *,
        usa_fecha_documento: bool,
    ) -> dict[str, Any]:
        fecha_efectiva: Any = "$$fecha_corte" if usa_fecha_documento else fecha
        return {
            "$lookup": {
                "from": COLECCION_SITUACION,
                "let": {"numero_prestamo": "$numero_prestamo", "fecha_corte": "$fecha_corte"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$NumeroPrestamo", "$$numero_prestamo"]},
                                    {"$eq": ["$fecha_corte", fecha_efectiva]},
                                ]
                            }
                        }
                    },
                    {"$limit": 1},
                ],
                "as": nombre,
            }
        }

    def _construir_pipeline(
        self,
        fecha_desde: str,
        fecha_hasta: str,
    ) -> list[dict[str, Any]]:
        pipeline: list[dict[str, Any]] = [
            {"$match": {"fecha_corte": {"$gte": fecha_desde, "$lte": fecha_hasta}}},
            {
                "$project": {
                    "fecha_corte": 1,
                    "numero_prestamo": {"$ifNull": ["$NUMERO_PRESTAMO", "$NumeroPrestamo"]},
                    "tipo_transaccion": {"$ifNull": ["$TIPO_TRANSACCION", "$TipoTransaccion"]},
                    "cobros": _cobros(),
                }
            },
        ]
        pipeline.extend([
            self._lookup_situacion("situacion", fecha_hasta, usa_fecha_documento=True),
            {"$unwind": {"path": "$situacion", "preserveNullAndEmptyArrays": True}},
            self._lookup_situacion("situacion_inicio", fecha_desde, usa_fecha_documento=False),
            {"$unwind": {"path": "$situacion_inicio", "preserveNullAndEmptyArrays": True}},
            self._lookup_situacion("situacion_fin", fecha_hasta, usa_fecha_documento=False),
            {"$unwind": {"path": "$situacion_fin", "preserveNullAndEmptyArrays": True}},
        ])
        pipeline.extend([
            {"$unwind": "$cobros"},
            {"$match": {"cobros.valor": {"$ne": 0}}},
        ])

        periodo = {
            "$concat": [
                {"$substrBytes": ["$fecha_corte", 0, 4]},
                "-",
                {"$substrBytes": ["$fecha_corte", 4, 2]},
            ]
        }
        identificador: dict[str, Any] = {
            "periodo": periodo,
            "anio": {"$toInt": {"$substrBytes": ["$fecha_corte", 0, 4]}},
            "mes": {"$toInt": {"$substrBytes": ["$fecha_corte", 4, 2]}},
        }
        identificador.update(CAMPO_GRUPO)
        pipeline.extend([
            {"$group": {"_id": identificador, "total_recuperado": {"$sum": "$cobros.valor"}}},
            {"$sort": {"_id.anio": 1, "_id.mes": 1, **{f"_id.{campo}": 1 for campo in TODOS_LOS_CAMPOS}}},
        ])
        return pipeline
