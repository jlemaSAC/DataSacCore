from datetime import datetime
from typing import Any

from fastapi import HTTPException
from pymongo.database import Database

from app.modules.analytic.indicadores_financieros.solvencia.repositories.sql_solvencia_repository import to_float

MongoDocument = dict[str, Any]


class MongoIndicadoresFinancierosRepository:
    situacion_crediticia_collection_name = "SituacionCrediticia"

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.situacion_crediticia_collection = mongo_db[
            self.situacion_crediticia_collection_name
        ]

    def get_provision_requerida_situacion_crediticia(
        self,
        *,
        fecha_corte: datetime,
        nombre_agencia: str | None,
    ) -> float:
        fecha_str = fecha_corte.strftime("%Y%m%d")
        match: dict[str, Any] = {"fecha_corte": fecha_str}
        if nombre_agencia:
            match["Agencia"] = nombre_agencia

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "provision_requerida": {
                        "$sum": {
                            "$convert": {
                                "input": "$ProvisionRequerida",
                                "to": "double",
                                "onError": 0,
                                "onNull": 0,
                            }
                        }
                    },
                }
            },
        ]
        rows = list(self.situacion_crediticia_collection.aggregate(pipeline))
        total = int(rows[0].get("total", 0)) if rows else 0
        provision_requerida = to_float(rows[0].get("provision_requerida")) if rows else 0.0

        if total == 0:
            raise HTTPException(
                status_code=422,
                detail=f"No hay datos en SituacionCrediticia para la fecha {fecha_str}.",
            )

        return provision_requerida
