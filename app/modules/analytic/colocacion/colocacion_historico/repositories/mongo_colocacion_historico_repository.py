from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from app.modules.analytic.colocacion.colocacion_historico.domain import (
    ColocacionAgrupada,
    DetalleColocacion,
    DimensionFiltroColocacion,
    DimensionesColocacion,
)


MongoDocument = dict[str, Any]


# Esta selección sostiene exclusivamente el resumen de Negocios.  El endpoint
# analítico conserva el conjunto dimensional completo.
CAMPOS_DIMENSION_RESUMEN = (
    "agencia",
    "condicion",
    "tipo_prestamo",
    "producto",
    "segmento",
    "asesor",
    "tasa_valor",
    "tasa_real_valor",
)

_VALORES_DIMENSION_NO_USADA: dict[str, str | float | int | None] = {
    "provincia": "SIN DATOS",
    "canton": "SIN DATOS",
    "parroquia": "SIN DATOS",
    "educacion": "SIN DATOS",
    "edad": "SIN DATOS",
    "garantia": "SIN DATOS",
    "monto": "SIN DATOS",
    "tasa": "SIN DATOS",
    "tasa_valor": None,
    "tasa_real": "SIN DATOS",
    "tasa_real_valor": None,
    "plazo": "SIN DATOS",
    "plazo_valor": None,
}


@dataclass(frozen=True)
class CorteMensual:
    anio: int
    mes: int
    fecha_corte: str
    fecha_inicio: datetime
    fecha_fin: datetime


def _texto_normalizado(*campos: str) -> dict[str, Any]:
    valor: Any = f"${campos[-1]}"
    for campo in reversed(campos[:-1]):
        valor = {"$ifNull": [f"${campo}", valor]}
    return {
        "$toUpper": {
            "$trim": {
                "input": {
                    "$convert": {
                        "input": valor,
                        "to": "string",
                        "onError": "SIN DATOS",
                        "onNull": "SIN DATOS",
                    }
                }
            }
        }
    }


def _rango_edad() -> dict[str, Any]:
    edad_convertida = {
        "$convert": {
            "input": "$Edad",
            "to": "int",
            "onError": None,
            "onNull": None,
        }
    }
    edad = {
        "$cond": [
            {"$gte": [edad_convertida, 0]},
            edad_convertida,
            None,
        ]
    }
    return {
        "$switch": {
            "branches": [
                {"case": {"$and": [{"$ne": [edad, None]}, {"$lte": [edad, 20]}]}, "then": "HASTA 20"},
                {"case": {"$and": [{"$ne": [edad, None]}, {"$lte": [edad, 30]}]}, "then": "HASTA 30"},
                {"case": {"$and": [{"$ne": [edad, None]}, {"$lte": [edad, 40]}]}, "then": "HASTA 40"},
                {"case": {"$and": [{"$ne": [edad, None]}, {"$lte": [edad, 50]}]}, "then": "HASTA 50"},
                {"case": {"$and": [{"$ne": [edad, None]}, {"$lte": [edad, 60]}]}, "then": "HASTA 60"},
                {"case": {"$and": [{"$ne": [edad, None]}, {"$lte": [edad, 70]}]}, "then": "HASTA 70"},
                {"case": {"$and": [{"$ne": [edad, None]}, {"$lte": [edad, 80]}]}, "then": "HASTA 80"},
                {"case": {"$and": [{"$ne": [edad, None]}, {"$lte": [edad, 90]}]}, "then": "HASTA 90"},
                {"case": {"$and": [{"$ne": [edad, None]}, {"$lte": [edad, 100]}]}, "then": "HASTA 100"},
                {"case": {"$gt": [edad, 100]}, "then": "MAS DE 100"},
            ],
            "default": "SIN DATOS",
        }
    }


def _rango_numerico(
    campo: str,
    rangos: tuple[tuple[float, str], ...],
    etiqueta_superior: str | None = None,
) -> dict[str, Any]:
    valor = _numero_valido(campo)
    branches = [
        {
            "case": {"$and": [{"$ne": [valor, None]}, {"$lte": [valor, limite]}]},
            "then": etiqueta,
        }
        for limite, etiqueta in rangos
    ]
    if etiqueta_superior:
        branches.append(
            {
                "case": {"$gt": [valor, rangos[-1][0]]},
                "then": etiqueta_superior,
            }
        )
    return {"$switch": {"branches": branches, "default": "SIN DATOS"}}


def _numero_valido(campo: str) -> dict[str, Any]:
    convertido = {
        "$convert": {
            "input": f"${campo}",
            "to": "double",
            "onError": None,
            "onNull": None,
        }
    }
    valor = {
        "$cond": [
            {"$gte": [convertido, 0]},
            convertido,
            None,
        ]
    }
    return valor


def _rango_plazo() -> dict[str, Any]:
    fecha_adjudicacion, fecha_vencimiento, fechas_validas = _fechas_plazo()
    rangos = (
        (1,  "Hasta 1 AÑO"),
        (2,  "Hasta 2 AÑOS"),
        (3,  "Hasta 3 AÑOS"),
        (4,  "Hasta 4 AÑOS"),
        (5,  "Hasta 5 AÑOS"),
        (6,  "Hasta 6 AÑOS"),
        (7,  "Hasta 7 AÑOS"),
        (8,  "Hasta 8 AÑOS"),
        (10, "Hasta 10 AÑOS"),
    )
    return {
        "$switch": {
            "branches": [
                {
                    "case": {
                        "$and": [
                            fechas_validas,
                            {
                                "$lte": [
                                    fecha_vencimiento,
                                    {
                                        "$dateAdd": {
                                            "startDate": fecha_adjudicacion,
                                            "unit": "year",
                                            "amount": anios,
                                        }
                                    },
                                ]
                            },
                        ]
                    },
                    "then": etiqueta,
                }
                for anios, etiqueta in rangos
            ],
            "default": {
                "$cond": [
                    fechas_validas,
                    "Mas de 10 AÑOS",
                    "SIN DATOS",
                ]
            },
        }
    }


def _plazo_dias() -> dict[str, Any]:
    fecha_adjudicacion, fecha_vencimiento, fechas_validas = _fechas_plazo()
    return {
        "$cond": [
            fechas_validas,
            {
                "$dateDiff": {
                    "startDate": fecha_adjudicacion,
                    "endDate": fecha_vencimiento,
                    "unit": "day",
                }
            },
            None,
        ]
    }


def _fechas_plazo() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    fecha_adjudicacion = {
        "$convert": {
            "input": "$FechaAdjudicacion",
            "to": "date",
            "onError": None,
            "onNull": None,
        }
    }
    fecha_vencimiento = {
        "$convert": {
            "input": "$FechaVencimiento",
            "to": "date",
            "onError": None,
            "onNull": None,
        }
    }
    fechas_validas = {
        "$and": [
            {"$ne": [fecha_adjudicacion, None]},
            {"$ne": [fecha_vencimiento, None]},
            {"$gte": [fecha_vencimiento, fecha_adjudicacion]},
        ]
    }
    return fecha_adjudicacion, fecha_vencimiento, fechas_validas


class MongoColocacionHistoricoRepository:
    collection_name = "SituacionCrediticia"

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.collection: Collection[MongoDocument] = mongo_db[self.collection_name]

    def obtener_colocaciones_agrupadas(
        self,
        cortes: list[CorteMensual],
        agencias: list[str] | None = None,
    ) -> list[ColocacionAgrupada]:
        return self._obtener_colocaciones_agrupadas(cortes, agencias)

    def obtener_colocaciones_resumen_agrupadas(
        self,
        cortes: list[CorteMensual],
        agencias: list[str] | None = None,
    ) -> list[ColocacionAgrupada]:
        """Agrupa el hecho histórico con las dimensiones que usa Negocios."""
        return self._obtener_colocaciones_agrupadas(
            cortes,
            agencias,
            CAMPOS_DIMENSION_RESUMEN,
        )

    def obtener_detalles_resumen(
        self,
        cortes: list[CorteMensual],
        agencias: list[str],
        dimension: DimensionFiltroColocacion,
        valor_dimension: str,
        asesores: list[str] | None = None,
    ) -> list[DetalleColocacion]:
        """Devuelve operaciones históricas con el mismo corte del resumen de Negocios."""
        if not cortes:
            return []

        rangos = [
            {
                "fecha_corte": corte.fecha_corte,
                "FechaAdjudicacion": {
                    "$gte": corte.fecha_inicio.isoformat(),
                    "$lte": corte.fecha_fin.isoformat(),
                },
            }
            for corte in cortes
        ]
        dimensiones = {
            "agencia": _texto_normalizado("Agencia"),
            "condicion": _texto_normalizado("TipoCondicion"),
            "tipo_prestamo": _texto_normalizado("TipoPrestamo"),
            "producto": _texto_normalizado("Producto"),
            "segmento": _texto_normalizado("Segmento"),
            "asesor": _texto_normalizado("NombreAsesor", "CodigoAsesor"),
            "tasa_normal": _numero_valido("TasaNominal"),
            "tasa_real": _numero_valido("TasaAnual"),
        }
        valor_dimension_normalizado: str | float | None = valor_dimension.strip().upper()
        if dimension in {"tasa_normal", "tasa_real"}:
            valor_dimension_normalizado = (
                None if valor_dimension.strip().upper() == "SIN DATOS" else float(valor_dimension)
            )
        condiciones = [
            {
                "$in": [
                    dimensiones["agencia"],
                    [agencia.strip().upper() for agencia in agencias],
                ]
            },
            {"$eq": [dimensiones[dimension], valor_dimension_normalizado]},
        ]
        if asesores:
            condiciones.append(
                {
                    "$in": [
                        dimensiones["asesor"],
                        [asesor.strip().upper() for asesor in asesores],
                    ]
                }
            )

        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "EstadoPrestamo": {"$ne": "CANCELADO"},
                    "$or": rangos,
                    "$expr": {"$and": condiciones},
                }
            },
            {
                "$project": {
                    "numero_cliente": _texto_normalizado("Cliente"),
                    "nombre_cliente": _texto_normalizado("Nombres"),
                    "numero_operacion": _texto_normalizado("NumeroPrestamo"),
                    "agencia": dimensiones["agencia"],
                    "asesor": dimensiones["asesor"],
                    "tipo_condicion": dimensiones["condicion"],
                    "producto": dimensiones["producto"],
                    "tipo_prestamo": dimensiones["tipo_prestamo"],
                    "segmento": dimensiones["segmento"],
                    "tasa_nominal": _numero_valido("TasaNominal"),
                    "tasa_real": _numero_valido("TasaAnual"),
                    "monto_colocado": {
                        "$convert": {
                            "input": "$DeudaInicial",
                            "to": "double",
                            "onError": 0,
                            "onNull": 0,
                        }
                    },
                }
            },
            {"$sort": {"numero_operacion": 1}},
        ]
        return [
            DetalleColocacion(
                numero_cliente=str(row.get("numero_cliente") or "SIN DATOS"),
                nombre_cliente=str(row.get("nombre_cliente") or "SIN DATOS"),
                numero_operacion=str(row.get("numero_operacion") or "SIN DATOS"),
                agencia=str(row.get("agencia") or "SIN DATOS"),
                asesor=str(row.get("asesor") or "SIN DATOS"),
                tipo_condicion=str(row.get("tipo_condicion") or "SIN DATOS"),
                producto=str(row.get("producto") or "SIN DATOS"),
                tipo_prestamo=str(row.get("tipo_prestamo") or "SIN DATOS"),
                segmento=str(row.get("segmento") or "SIN DATOS"),
                tasa_nominal=_numero_detalle(row.get("tasa_nominal")),
                tasa_real=_numero_detalle(row.get("tasa_real")),
                monto_colocado=float(row.get("monto_colocado") or 0.0),
            )
            for row in self.collection.aggregate(
                pipeline,
                hint="fecha_corte_1",
                allowDiskUse=True,
            )
        ]

    def _obtener_colocaciones_agrupadas(
        self,
        cortes: list[CorteMensual],
        agencias: list[str] | None,
        campos_dimension: tuple[str, ...] | None = None,
    ) -> list[ColocacionAgrupada]:
        if not cortes:
            return []

        periodo_por_fecha_corte = {
            corte.fecha_corte: (corte.anio, corte.mes)
            for corte in cortes
        }
        rangos = [
            {
                "fecha_corte": corte.fecha_corte,
                "FechaAdjudicacion": {
                    "$gte": corte.fecha_inicio.isoformat(),
                    "$lte": corte.fecha_fin.isoformat(),
                },
            }
            for corte in cortes
        ]
        dimensiones = {
            "agencia": _texto_normalizado("Agencia"),
            "condicion": _texto_normalizado("TipoCondicion"),
            "tipo_prestamo": _texto_normalizado("TipoPrestamo"),
            "producto": _texto_normalizado("Producto"),
            "segmento": _texto_normalizado("Segmento"),
            "asesor": _texto_normalizado("NombreAsesor", "CodigoAsesor"),
            "provincia": _texto_normalizado("Provincia"),
            "canton": _texto_normalizado("Canton"),
            "parroquia": _texto_normalizado("Parroquia"),
            "educacion": _texto_normalizado(
                "Educacion",
                "Educación",
                "NivelEducacion",
                "NivelDeEducacion",
            ),
            "edad": _rango_edad(),
            "garantia": _texto_normalizado(
                "TipoDeGarantia",
                "TipoGarantia",
                "GarantiaTipo",
            ),
            "monto": _rango_numerico(
                "DeudaInicial",
                (
                    (3000,   "Hasta 3.000"),
                    (5000,   "Hasta 5.000"),
                    (8000,   "Hasta 8.000"),
                    (10000,  "Hasta 10.000"),
                    (20000,  "Hasta 20.000"),
                    (30000,  "Hasta 30.000"),
                    (40000,  "Hasta 40.000"),
                    (50000,  "Hasta 50.000"),
                    (60000,  "Hasta 60.000"),
                    (70000,  "Hasta 70.000"),
                    (80000,  "Hasta 80.000"),
                    (90000,  "Hasta 90.000"),
                    (100000, "Hasta 100.000"),
                ),
                "Mas de 100.000",
            ),
            "tasa": _rango_numerico(
                "TasaNominal",
                (
                    (13, "Hasta 13"),
                    (14, "Hasta 14"),
                    (16, "Hasta 16"),
                    (17, "Hasta 17"),
                    (18, "Hasta 18"),
                    (19, "Hasta 19"),
                    (20, "Hasta 20"),
                    (21, "Hasta 21"),
                ),
                "Mas de 22",
            ),
            "tasa_valor": _numero_valido("TasaNominal"),
            "tasa_real": _rango_numerico(
                "TasaAnual",
                (
                    (13, "Hasta 13"),
                    (14, "Hasta 14"),
                    (16, "Hasta 16"),
                    (17, "Hasta 17"),
                    (18, "Hasta 18"),
                    (19, "Hasta 19"),
                    (20, "Hasta 20"),
                    (21, "Hasta 21"),
                ),
                "Mas de 22",
            ),
            "tasa_real_valor": _numero_valido("TasaAnual"),
            "plazo": _rango_plazo(),
            "plazo_valor": _plazo_dias(),
        }
        campos = campos_dimension or tuple(dimensiones)
        filtros: dict[str, Any] = {"EstadoPrestamo": {"$ne": "CANCELADO"}, "$or": rangos}
        if agencias:
            filtros["$expr"] = {
                "$in": [_texto_normalizado("Agencia"), [agencia.strip().upper() for agencia in agencias]]
            }

        pipeline: list[dict[str, Any]] = [
            {"$match": filtros},
            {
                "$project": {
                    "fecha_corte": 1,
                    **{campo: dimensiones[campo] for campo in campos},
                    "deuda_inicial": {
                        "$convert": {
                            "input": "$DeudaInicial",
                            "to": "double",
                            "onError": 0,
                            "onNull": 0,
                        }
                    },
                }
            },
            {
                "$group": {
                    "_id": {
                        "fecha_corte": "$fecha_corte",
                        **{campo: f"${campo}" for campo in campos},
                    },
                    "operaciones": {"$sum": 1},
                    "saldo_inicial": {"$sum": "$deuda_inicial"},
                }
            },
        ]

        rows = self.collection.aggregate(
            pipeline,
            hint="fecha_corte_1",
            allowDiskUse=True,
        )
        resultado: list[ColocacionAgrupada] = []
        for row in rows:
            identificador = row.get("_id") or {}
            periodo = periodo_por_fecha_corte.get(str(identificador.get("fecha_corte") or ""))
            if periodo is None:
                continue
            anio, mes = periodo
            valores = dict(_VALORES_DIMENSION_NO_USADA)
            for campo in dimensiones:
                if campo not in campos:
                    continue
                if campo in {"tasa_valor", "tasa_real_valor"}:
                    valor_tasa = identificador.get(campo)
                    valores[campo] = (
                        float(valor_tasa)
                        if isinstance(valor_tasa, int | float) and valor_tasa >= 0
                        else None
                    )
                    continue
                if campo == "plazo_valor":
                    valor_plazo = identificador.get(campo)
                    valores[campo] = (
                        int(valor_plazo)
                        if isinstance(valor_plazo, int | float) and valor_plazo >= 0
                        else None
                    )
                    continue
                valor = str(identificador.get(campo) or "SIN DATOS").strip() or "SIN DATOS"
                valores[campo] = valor if campo in {"monto", "tasa", "tasa_real", "plazo"} else valor.upper()
            resultado.append(
                ColocacionAgrupada(
                    dimensiones=DimensionesColocacion(
                        periodo=f"{anio:04d}-{mes:02d}",
                        anio=anio,
                        mes=mes,
                        **valores,
                    ),
                    operaciones=int(row.get("operaciones") or 0),
                    saldo_inicial=float(row.get("saldo_inicial") or 0.0),
                )
            )
        return resultado


def _numero_detalle(valor: object) -> float | None:
    return float(valor) if isinstance(valor, int | float) and valor >= 0 else None
