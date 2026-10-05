from __future__ import annotations

from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database


MongoDocument = dict[str, Any]


class MongoResumenDiarioCarteraRepository:
    actual_collection_name = "SituacionCrediticiaActual"
    historico_collection_name = "SituacionCrediticia"

    projection = {
        "NumeroPrestamo": 1,
        "CodigoUsuario": 1,
        "CodigoAsesor": 1,
        "CODIGOUSUARIO": 1,
        "NombreAsesor": 1,
        "NombreCompleto": 1,
        "Agencia": 1,
        "EstadoPrestamo": 1,
        "SaldoCapital": 1,
        "ProvisionRequerida": 1,
        "CapitalNoDevenga": 1,
        "CapitalVencido": 1,
        "DiasVencidos": 1,
    }

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.actual: Collection[MongoDocument] = mongo_db[self.actual_collection_name]
        self.historico: Collection[MongoDocument] = mongo_db[self.historico_collection_name]

    def obtener_snapshots_por_agencia(
        self,
        *,
        agencia: str,
        fecha_corte_ayer: str,
    ) -> dict[str, list[MongoDocument]]:
        filtro_agencia = {"Agencia": agencia.strip()}
        filtro_vigentes = {"EstadoPrestamo": {"$ne": "CANCELADO"}}
        filtro_actual = {"$and": [filtro_agencia, filtro_vigentes]}
        filtro_historico = {
            "$and": [filtro_agencia, filtro_vigentes, {"fecha_corte": fecha_corte_ayer}]
        }
        documentos_hoy = list(self.actual.find(filtro_actual, self.projection))
        documentos_ayer = list(self.historico.find(filtro_historico, self.projection))
        return {"hoy": documentos_hoy, "ayer": documentos_ayer}
