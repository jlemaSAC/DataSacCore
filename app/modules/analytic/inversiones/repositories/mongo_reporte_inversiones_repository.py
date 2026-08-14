from typing import Any

from pymongo import ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database

from app.modules.analytic.inversiones.constants import REPORTE_INVERSIONES_COLLECTION


MongoDocument = dict[str, Any]
class MongoReporteInversionesRepository:
    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.collection: Collection[MongoDocument] = mongo_db[REPORTE_INVERSIONES_COLLECTION]

    def ensure_indexes(self) -> None:
        self.collection.create_index(
            [("periodo", ASCENDING), ("fecha_corte", ASCENDING)],
            name="idx_reporte_inversiones_periodo_corte",
        )

    def obtener_periodos_cargados(self, periodos: list[str]) -> set[str]:
        if not periodos:
            return set()
        return {
            str(periodo)
            for periodo in self.collection.distinct("periodo", {"periodo": {"$in": periodos}})
            if periodo
        }

    def obtener_filas(self, periodos: list[str]) -> list[MongoDocument]:
        if not periodos:
            return []
        return list(
            self.collection.find(
                {"periodo": {"$in": periodos}},
                {"_id": 0},
            ).sort([("fecha_corte", ASCENDING)])
        )
