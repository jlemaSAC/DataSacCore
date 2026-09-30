from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database


MongoDocument = dict[str, Any]


class MongoSituacionCrediticiaAsesoresRepository:
    """Lee los dos snapshots Mongo usados por la comparación de asesores."""

    actual_collection_name = "SituacionCrediticiaActual"
    historico_collection_name = "SituacionCrediticia"

    projection = {
        "_id": 0,
        "fecha_corte": 1,
        "NumeroPrestamo": 1,
        "CodigoUsuario": 1,
        "CodigoAsesor": 1,
        "NombreAsesor": 1,
        "CargoAsesor": 1,
        "Agencia": 1,
        "IdAgencia": 1,
        "id_agencia": 1,
        "Cliente": 1,
        "EstadoPrestamo": 1,
        "CodigoEstadoPrestamo": 1,
        "CodigoEstado": 1,
        "SaldoCapital": 1,
        "CapitalVigente": 1,
        "CapitalNoDevenga": 1,
        "CapitalVencido": 1,
        "ProvisionRequerida": 1,
        "ProvisionRequeridaCalculada": 1,
        "ESDIFERIDO": 1,
        "EsDiferido": 1,
        "Diferido": 1,
    }

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.actual: Collection[MongoDocument] = mongo_db[self.actual_collection_name]
        self.historico: Collection[MongoDocument] = mongo_db[self.historico_collection_name]

    def obtener_ultimo_corte_actual(self) -> str | None:
        document = self.actual.find_one(
            {"as_of": {"$exists": True}},
            {"_id": 0, "as_of": 1},
            sort=[("as_of", -1)],
        )
        if not document or document.get("as_of") is None:
            return None
        return _formatear_fecha_corte(document["as_of"])

    def obtener_actual(
        self,
        fecha_corte: str | None,
        agencia_nombre: str | None = None,
    ) -> list[MongoDocument]:
        return self._obtener(
            self.actual,
            fecha_corte=None,
            agencia_nombre=agencia_nombre,
        )

    def obtener_historico(
        self,
        fecha_corte: str,
        agencia_nombre: str | None = None,
    ) -> list[MongoDocument]:
        return self._obtener(
            self.historico,
            fecha_corte=fecha_corte,
            agencia_nombre=agencia_nombre,
        )

    def _obtener(
        self,
        collection: Collection[MongoDocument],
        *,
        fecha_corte: str | None,
        agencia_nombre: str | None,
    ) -> list[MongoDocument]:
        match: MongoDocument = {"EstadoPrestamo": {"$ne": "CANCELADO"}}
        if fecha_corte:
            match["fecha_corte"] = fecha_corte
        if agencia_nombre:
            match["Agencia"] = agencia_nombre

        cursor = collection.find(match, projection=self.projection)
        return list(cursor)


def _formatear_fecha_corte(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y%m%d")

    texto = str(value).strip()
    if len(texto) >= 8 and texto[:8].isdigit():
        return texto[:8]

    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).strftime("%Y%m%d")
    except ValueError:
        return texto
