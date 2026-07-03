from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from app.modules.prestamos.constants import (
    SITUACION_CREDITICIA_ACTUAL_COLLECTION,
    SITUACION_CREDITICIA_HISTORICO_COLLECTION,
)
from app.modules.prestamos.filtros import build_mongo_match_actual, build_mongo_match_historico
from app.modules.prestamos.mappers import prestamo_snapshot_from_mongo
from app.modules.prestamos.schemas import PrestamoSnapshot, PrestamoUniverseRequest


MongoDocument = dict[str, Any]


class MongoUniversoPrestamosRepository:
    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.situacion_crediticia_actual_collection: Collection[MongoDocument] = mongo_db[
            SITUACION_CREDITICIA_ACTUAL_COLLECTION
        ]
        self.situacion_crediticia_historico_collection: Collection[MongoDocument] = mongo_db[
            SITUACION_CREDITICIA_HISTORICO_COLLECTION
        ]

    def get_actual_snapshots(self, filtros: PrestamoUniverseRequest) -> list[PrestamoSnapshot]:
        return self._find_snapshots(self.situacion_crediticia_actual_collection, build_mongo_match_actual(filtros))

    def get_historico_snapshots(self, filtros: PrestamoUniverseRequest) -> list[PrestamoSnapshot]:
        return self._find_snapshots(
            self.situacion_crediticia_historico_collection,
            build_mongo_match_historico(filtros),
        )

    def _find_snapshots(
        self,
        collection: Collection[MongoDocument],
        match: dict[str, Any],
    ) -> list[PrestamoSnapshot]:
        return [prestamo_snapshot_from_mongo(document) for document in collection.find(match)]
