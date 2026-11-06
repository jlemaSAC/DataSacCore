from datetime import date
from typing import Any

from pymongo.database import Database

from app.modules.analytic.ahorro_vista.constants import REPORTE_AHORRO_VISTA_COLLECTION


class MongoResumenAhorroVistaRepository:
    def __init__(self, db: Database) -> None:
        self.collection = db[REPORTE_AHORRO_VISTA_COLLECTION]

    def obtener_corte(self, fecha: date) -> list[dict[str, Any]] | None:
        # Reducir el corte en el servidor: no transportar ~100 mil filas analíticas.
        dimensiones = ("agencia", "asesor", "estado", "producto_ahorro", "tasa_decimal")
        filas = list(self.collection.aggregate([
            {"$match": {
                "fecha_corte": fecha.strftime("%Y%m%d"),
                "es_programado": False,
            }},
            {"$group": {
                "_id": {campo: f"${campo}" for campo in dimensiones},
                "saldo": {"$sum": "$saldo"},
                "numero_cuentas": {"$sum": "$numero_cuentas"},
                "incompletas": {"$sum": {"$cond": [
                    {"$or": [
                        {"$eq": [{"$ifNull": ["$numero_cuentas", None]}, None]},
                        {"$eq": [{"$ifNull": ["$tasa_decimal", None]}, None]},
                    ]}, 1, 0,
                ]}},
            }},
        ]))
        # Un documento agregado no equivale a una cuenta. Los cortes antiguos
        # sin conteo se reconstruyen en SQL en lugar de inventar cantidades.
        if not filas or any(fila["incompletas"] for fila in filas):
            return None
        return [dict(fila["_id"], saldo=fila["saldo"], numero_cuentas=fila["numero_cuentas"]) for fila in filas]
