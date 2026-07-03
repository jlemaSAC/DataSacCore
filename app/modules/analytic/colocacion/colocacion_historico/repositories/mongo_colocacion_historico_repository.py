from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database


MongoDocument = dict[str, Any]


@dataclass(frozen=True)
class CorteMensual:
    mes: int
    fecha_corte: str
    fecha_inicio: datetime
    fecha_fin: datetime


class MongoColocacionHistoricoRepository:
    collection_name = "SituacionCrediticia"

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.collection: Collection[MongoDocument] = mongo_db[self.collection_name]

    def obtener_saldos_iniciales_por_cortes(
        self,
        cortes: list[CorteMensual],
    ) -> dict[int, dict[str, float]]:
        if not cortes:
            return {}

        mes_por_fecha_corte = {corte.fecha_corte: corte.mes for corte in cortes}
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
        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "EstadoPrestamo": {"$ne": "CANCELADO"},
                    "$or": rangos,
                }
            },
            {
                "$project": {
                    "fecha_corte": 1,
                    "agencia": {
                        "$toUpper": {
                            "$trim": {
                                "input": {
                                    "$convert": {
                                        "input": "$Agencia",
                                        "to": "string",
                                        "onError": "SIN DATOS",
                                        "onNull": "SIN DATOS",
                                    }
                                }
                            }
                        }
                    },
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
                        "agencia": "$agencia",
                    },
                    "saldo_inicial": {"$sum": "$deuda_inicial"},
                }
            },
        ]

        rows = self.collection.aggregate(pipeline, hint="fecha_corte_1")
        saldos: dict[int, dict[str, float]] = {}
        for row in rows:
            identificador = row.get("_id") or {}
            mes = mes_por_fecha_corte.get(str(identificador.get("fecha_corte") or ""))
            if mes is None:
                continue
            agencia = str(identificador.get("agencia") or "SIN DATOS").strip().upper()
            agencia = agencia or "SIN DATOS"
            saldos.setdefault(mes, {})[agencia] = float(row.get("saldo_inicial") or 0.0)
        return saldos
