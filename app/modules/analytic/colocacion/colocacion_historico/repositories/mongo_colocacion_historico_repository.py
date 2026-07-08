from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from app.modules.analytic.colocacion.colocacion_historico.domain import (
    ColocacionAgrupada,
    DimensionesColocacion,
)


MongoDocument = dict[str, Any]


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


class MongoColocacionHistoricoRepository:
    collection_name = "SituacionCrediticia"

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.collection: Collection[MongoDocument] = mongo_db[self.collection_name]

    def obtener_colocaciones_agrupadas(
        self,
        cortes: list[CorteMensual],
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
        }
        pipeline: list[dict[str, Any]] = [
            {"$match": {"EstadoPrestamo": {"$ne": "CANCELADO"}, "$or": rangos}},
            {
                "$project": {
                    "fecha_corte": 1,
                    **dimensiones,
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
                        **{campo: f"${campo}" for campo in dimensiones},
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
            valores = {
                campo: str(identificador.get(campo) or "SIN DATOS").strip().upper()
                or "SIN DATOS"
                for campo in dimensiones
            }
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
