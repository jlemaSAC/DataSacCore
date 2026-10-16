from datetime import date, timedelta
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database


MongoDocument = dict[str, Any]
COLECCION_RECUPERACION = "RecuperacionCrediticia"
COLECCION_RECUPERACION_ACTUAL = "RecuperacionCrediticiaActual"
COLECCION_SITUACION = "SituacionCrediticia"
COLECCION_SITUACION_ACTUAL = "SituacionCrediticiaActual"
PATRON_TIPO_TRANSACCION = r"^ABONO PR.STAMO DESDE CUENTA(?:$|\s)"
ESTADOS_INCLUIDOS = ["CASTIGADO", "JUDICIAL", "T", "J"]
CAMPOS_MONTO = (
    "TOTAL_RECUPERADO",
    "CAPITAL",
    "INTERES",
    "INTERES_MORA",
    "SEGURO",
    "COBRANZA",
    "JUDICIAL",
    "DIFERIDO",
    "OTROS",
)


def _texto_normalizado(campo: Any) -> dict[str, Any]:
    return {
        "$toUpper": {
            "$trim": {
                "input": {
                    "$convert": {
                        "input": campo,
                        "to": "string",
                        "onError": "",
                        "onNull": "",
                    }
                }
            }
        }
    }


def _numero(campo: str) -> dict[str, Any]:
    return {
        "$convert": {
            "input": campo,
            "to": "double",
            "onError": 0,
            "onNull": 0,
        }
    }


def _nombre_campo_alternativo(campo: str) -> str:
    """Nombre camel case utilizado por algunas versiones de los documentos."""
    return "".join(parte.title() for parte in campo.lower().split("_"))


class MongoCastigoRepository:
    """Agrega depósitos diarios desde las colecciones de recuperaciones Mongo."""

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.historico: Collection[MongoDocument] = mongo_db[COLECCION_RECUPERACION]
        self.actual: Collection[MongoDocument] = mongo_db[COLECCION_RECUPERACION_ACTUAL]

    def obtener_depositos_diarios(
        self,
        fecha_desde: date,
        fecha_hasta: date,
        fecha_actual: date,
        agencias: list[str],
        asesores: list[str],
        cargos: list[str],
    ) -> dict[str, Any]:
        consultas: list[tuple[Collection[MongoDocument], str, str]] = []
        ayer = fecha_actual - timedelta(days=1)
        fecha_historica_hasta = min(fecha_hasta, ayer)

        if fecha_desde <= fecha_historica_hasta:
            consultas.append(
                (
                    self.historico,
                    fecha_desde.strftime("%Y%m%d"),
                    fecha_historica_hasta.strftime("%Y%m%d"),
                )
            )
        if fecha_desde <= fecha_actual <= fecha_hasta:
            fecha_hoy = fecha_actual.strftime("%Y%m%d")
            consultas.append((self.actual, fecha_hoy, fecha_hoy))

        depositos_por_clave: dict[tuple[Any, ...], dict[str, Any]] = {}
        catalogos = {"agencias": set(), "asesores": set(), "cargos": set()}
        for collection, desde, hasta in consultas:
            pipeline = self._construir_pipeline(
                desde=desde,
                hasta=hasta,
                fecha_inicio=fecha_desde.strftime("%Y%m%d"),
                fecha_fin=fecha_hasta.strftime("%Y%m%d"),
                fecha_actual=fecha_actual.strftime("%Y%m%d"),
                agencias=agencias,
                asesores=asesores,
                cargos=cargos,
            )
            documento = next(iter(collection.aggregate(pipeline, allowDiskUse=True)), {})
            for campo, campo_pipeline in (
                ("agencias", "agencia"),
                ("asesores", "asesor"),
                ("cargos", "cargo_asesor"),
            ):
                catalogos[campo].update(
                    str(item["_id"])
                    for item in documento.get(campo_pipeline, [])
                    if item.get("_id")
                )
            for fila in documento.get("depositos", []):
                clave = tuple(
                    fila.get("_id", {}).get(campo)
                    for campo in (
                        "fecha",
                        "numero_prestamo",
                        "estado_prestamo_inicio",
                        "estado_prestamo_fin",
                        "tipo_transaccion",
                        "agencia",
                        "codigo_asesor",
                        "asesor",
                        "cargo_asesor",
                    )
                )
                acumulado = depositos_por_clave.setdefault(
                    clave,
                    {**fila, **{campo.lower(): 0.0 for campo in CAMPOS_MONTO}},
                )
                for campo in CAMPOS_MONTO:
                    acumulado[campo.lower()] += float(fila.get(campo.lower()) or 0)

        depositos = list(depositos_por_clave.values())
        depositos.sort(
            key=lambda fila: (
                fila.get("_id", {}).get("fecha", ""),
                fila.get("_id", {}).get("numero_prestamo", ""),
                fila.get("_id", {}).get("agencia", ""),
                fila.get("_id", {}).get("asesor", ""),
            )
        )
        return {
            "depositos": depositos,
            "catalogos": {campo: sorted(valores) for campo, valores in catalogos.items()},
        }

    @staticmethod
    def _construir_pipeline(
        *,
        desde: str,
        hasta: str,
        fecha_inicio: str,
        fecha_fin: str,
        fecha_actual: str,
        agencias: list[str],
        asesores: list[str],
        cargos: list[str],
    ) -> list[dict[str, Any]]:
        pipeline: list[dict[str, Any]] = [
            {"$match": {"fecha_corte": {"$gte": desde, "$lte": hasta}}},
            {
                "$project": {
                    "fecha": "$fecha_corte",
                    "numero_prestamo": {
                        "$trim": {
                            "input": {
                                "$convert": {
                                    "input": {"$ifNull": ["$NUMERO_PRESTAMO", "$NumeroPrestamo"]},
                                    "to": "string",
                                    "onError": "",
                                    "onNull": "",
                                }
                            }
                        }
                    },
                    "tipo_transaccion": _texto_normalizado(
                        {"$ifNull": ["$TIPO_TRANSACCION", "$TipoTransaccion"]}
                    ),
                    "agencia": _texto_normalizado("$AGENCIA"),
                    "codigo_asesor": {
                        "$trim": {
                            "input": {
                                "$convert": {
                                    "input": "$CODIGO_ASESOR_COBRO",
                                    "to": "string",
                                    "onError": "",
                                    "onNull": "",
                                }
                            }
                        }
                    },
                    "asesor": _texto_normalizado(
                        {"$ifNull": ["$NOMBRE_ASESOR_COBRO", "$CODIGO_ASESOR_COBRO"]}
                    ),
                    "cargo_asesor": _texto_normalizado("$CARGO_ASESOR_COBRO"),
                    **{
                        campo.lower(): _numero(
                            {"$ifNull": [f"${campo}", f"${_nombre_campo_alternativo(campo)}"]}
                        )
                        for campo in CAMPOS_MONTO
                    },
                }
            },
            {
                "$match": {
                    "numero_prestamo": {"$ne": ""},
                    "tipo_transaccion": {
                        "$regex": PATRON_TIPO_TRANSACCION,
                        "$options": "i",
                    },
                }
            },
            *_lookup_estado_corte("inicio", fecha_inicio, fecha_actual),
            {"$match": {"estado_prestamo_inicio": {"$in": ESTADOS_INCLUIDOS}}},
            *_lookup_estado_corte("fin", fecha_fin, fecha_actual),
            {
                "$set": {
                    "total_recuperado": {
                        "$cond": [
                            {"$gt": ["$total_recuperado", 0]},
                            "$total_recuperado",
                            {
                                "$add": [
                                    "$capital",
                                    "$interes",
                                    "$interes_mora",
                                    "$seguro",
                                    "$cobranza",
                                    "$judicial",
                                    "$diferido",
                                    "$otros",
                                ]
                            },
                        ]
                    }
                }
            },
            {
                "$facet": {
                    "depositos": [
                        *_filtros_dimensiones(agencias, asesores, cargos),
                        {
                            "$group": {
                                "_id": {
                                    "fecha": "$fecha",
                                    "numero_prestamo": "$numero_prestamo",
                                    "estado_prestamo_inicio": "$estado_prestamo_inicio",
                                    "estado_prestamo_fin": "$estado_prestamo_fin",
                                    "tipo_transaccion": "$tipo_transaccion",
                                    "agencia": "$agencia",
                                    "codigo_asesor": "$codigo_asesor",
                                    "asesor": "$asesor",
                                    "cargo_asesor": "$cargo_asesor",
                                },
                                **{
                                    campo.lower(): {"$sum": f"${campo.lower()}"}
                                    for campo in CAMPOS_MONTO
                                },
                            }
                        },
                        {"$sort": {"_id.fecha": 1, "_id.numero_prestamo": 1}},
                    ],
                    **{
                        campo: [
                            {"$match": {campo: {"$ne": ""}}},
                            {"$group": {"_id": f"${campo}"}},
                            {"$sort": {"_id": 1}},
                        ]
                        for campo in ("agencia", "asesor", "cargo_asesor")
                    },
                }
            },
        ]
        return pipeline


def _filtros_dimensiones(
    agencias: list[str], asesores: list[str], cargos: list[str]
) -> list[dict[str, Any]]:
    filtros = []
    for campo, valores in (
        ("agencia", agencias),
        ("asesor", asesores),
        ("cargo_asesor", cargos),
    ):
        if valores:
            filtros.append({"$match": {campo: {"$in": valores}}})
    return filtros


def _lookup_estado_corte(
    nombre: str,
    fecha_corte: str,
    fecha_actual: str,
) -> list[dict[str, Any]]:
    proyeccion = {
        "_id": 0,
        "EstadoPrestamo": 1,
        "CodigoEstadoPrestamo": 1,
        "CodigoEstado": 1,
    }
    situacion = f"situacion_{nombre}"
    estado = f"estado_prestamo_{nombre}"
    if fecha_corte == fecha_actual:
        fecha_anterior = (
            date(
                int(fecha_actual[:4]),
                int(fecha_actual[4:6]),
                int(fecha_actual[6:]),
            )
            - timedelta(days=1)
        ).strftime("%Y%m%d")
        lookup_actual = _lookup_situacion(
            COLECCION_SITUACION_ACTUAL,
            f"{situacion}_actual",
            proyeccion,
        )
        lookup_historico = _lookup_situacion(
            COLECCION_SITUACION,
            f"{situacion}_historica",
            proyeccion,
            fecha_corte=fecha_anterior,
        )
        stages = [
            lookup_actual,
            lookup_historico,
            {
                "$set": {
                    situacion: {
                        "$ifNull": [
                            {"$arrayElemAt": [f"${situacion}_actual", 0]},
                            {"$arrayElemAt": [f"${situacion}_historica", 0]},
                        ]
                    }
                }
            },
        ]
    else:
        stages = [
            _lookup_situacion(
                COLECCION_SITUACION,
                situacion,
                proyeccion,
                fecha_corte=fecha_corte,
            )
        ]

    stages.extend(
        [
            {"$unwind": f"${situacion}"},
            {
                "$set": {
                    estado: _texto_normalizado(
                        {
                            "$ifNull": [
                                f"${situacion}.EstadoPrestamo",
                                {
                                    "$ifNull": [
                                        f"${situacion}.CodigoEstadoPrestamo",
                                        f"${situacion}.CodigoEstado",
                                    ]
                                },
                            ]
                        }
                    )
                }
            },
        ]
    )
    return stages


def _lookup_situacion(
    coleccion: str,
    alias: str,
    proyeccion: dict[str, int],
    *,
    fecha_corte: str | None = None,
) -> dict[str, Any]:
    condiciones = [{"$eq": ["$NumeroPrestamo", "$$numero"]}]
    if fecha_corte is not None:
        condiciones.append({"$eq": ["$fecha_corte", fecha_corte]})
    return {
        "$lookup": {
            "from": coleccion,
            "let": {"numero": "$numero_prestamo"},
            "pipeline": [
                {"$match": {"$expr": {"$and": condiciones}}},
                {"$project": proyeccion},
                {"$limit": 1},
            ],
            "as": alias,
        }
    }
