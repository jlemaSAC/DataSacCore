from typing import Any

from pymongo import ASCENDING, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database

from app.modules.prestamos.constants import (
    SITUACION_CREDITICIA_ACTUAL_COLLECTION,
    SITUACION_CREDITICIA_HISTORICO_COLLECTION,
)
from app.modules.prestamos.filtros import build_mongo_match_actual, build_mongo_match_historico
from app.modules.prestamos.mappers import mongo_document_from_snapshot, prestamo_snapshot_from_mongo
from app.modules.prestamos.schemas import PrestamoSnapshot, PrestamoUniverseRequest

MongoDocument = dict[str, Any]


class MongoUniversoPrestamosRepository:
    situacion_crediticia_actual_collection_name = SITUACION_CREDITICIA_ACTUAL_COLLECTION
    situacion_crediticia_historico_collection_name = SITUACION_CREDITICIA_HISTORICO_COLLECTION

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.situacion_crediticia_actual_collection: Collection[MongoDocument] = mongo_db[
            self.situacion_crediticia_actual_collection_name
        ]
        self.situacion_crediticia_historico_collection: Collection[MongoDocument] = mongo_db[
            self.situacion_crediticia_historico_collection_name
        ]
        self._actual_indexes_ensured = False

    def get_actual_snapshots(self, filtros: PrestamoUniverseRequest) -> list[PrestamoSnapshot]:
        return self._find_snapshots(self.situacion_crediticia_actual_collection, build_mongo_match_actual(filtros))

    def get_historico_snapshots(self, filtros: PrestamoUniverseRequest) -> list[PrestamoSnapshot]:
        return self._find_snapshots(
            self.situacion_crediticia_historico_collection,
            build_mongo_match_historico(filtros),
        )

    def ensure_actual_indexes(self) -> None:
        if self._actual_indexes_ensured:
            return

        self.situacion_crediticia_actual_collection.create_index(
            [("IdPrestamo", ASCENDING)],
            unique=True,
            name="idx_situacion_crediticia_actual_id_prestamo",
        )
        self.situacion_crediticia_actual_collection.create_index(
            [("NumeroPrestamo", ASCENDING)],
            name="idx_situacion_crediticia_actual_numero_prestamo",
        )
        self.situacion_crediticia_actual_collection.create_index(
            [("CodigoAsesor", ASCENDING)],
            name="idx_situacion_crediticia_actual_codigo_asesor",
        )
        self.situacion_crediticia_actual_collection.create_index(
            [("IdAgencia", ASCENDING)],
            name="idx_situacion_crediticia_actual_id_agencia",
        )
        self.situacion_crediticia_actual_collection.create_index(
            [("EsDiferido", ASCENDING)],
            name="idx_situacion_crediticia_actual_es_diferido",
        )
        self.situacion_crediticia_actual_collection.create_index(
            [("DiasVencidos", ASCENDING)],
            name="idx_situacion_crediticia_actual_dias_vencidos",
        )
        self.situacion_crediticia_actual_collection.create_index(
            [("data_version", ASCENDING)],
            name="idx_situacion_crediticia_actual_data_version",
        )
        self._actual_indexes_ensured = True

    def upsert_actual_snapshots(
        self,
        snapshots: list[PrestamoSnapshot],
        *,
        as_of,
        data_version: str,
    ) -> dict[str, int]:
        operations = []
        for snapshot in snapshots:
            document = mongo_document_from_snapshot(snapshot, as_of=as_of, data_version=data_version)
            operations.append(
                UpdateOne(
                    {"IdPrestamo": document["IdPrestamo"]},
                    {"$set": document},
                    upsert=True,
                )
            )

        if not operations:
            return {"upserted": 0, "matched": 0, "modified": 0}

        result = self.situacion_crediticia_actual_collection.bulk_write(operations, ordered=False)
        return {
            "upserted": int(result.upserted_count),
            "matched": int(result.matched_count),
            "modified": int(result.modified_count),
        }

    def _find_snapshots(
        self,
        collection: Collection[MongoDocument],
        match: dict[str, Any],
    ) -> list[PrestamoSnapshot]:
        return [prestamo_snapshot_from_mongo(document) for document in collection.find(match)]
