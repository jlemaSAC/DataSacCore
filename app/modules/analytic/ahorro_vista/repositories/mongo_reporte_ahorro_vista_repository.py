from datetime import date
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from app.modules.analytic.ahorro_vista.constants import REPORTE_AHORRO_VISTA_COLLECTION


MongoDocument = dict[str, Any]


class MongoReporteAhorroVistaRepository:
    """Consulta cortes mensuales finalizados cargados por DataSacETL."""

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.collection: Collection[MongoDocument] = mongo_db[REPORTE_AHORRO_VISTA_COLLECTION]

    def obtener_por_mes(
        self,
        mes: date,
        es_programado: bool | None = None,
    ) -> list[MongoDocument]:
        fecha_desde = f"{mes:%Y%m}01"
        fecha_hasta = f"{_primer_dia_mes_siguiente(mes):%Y%m}01"
        filtro: MongoDocument = {"fecha_corte": {"$gte": fecha_desde, "$lt": fecha_hasta}}
        if es_programado is not None:
            filtro["es_programado"] = es_programado
        return list(self.collection.find(filtro, {"_id": 0}))

    def existe_corte_mensual(self, mes: date) -> bool:
        fecha_desde = f"{mes:%Y%m}01"
        fecha_hasta = f"{_primer_dia_mes_siguiente(mes):%Y%m}01"
        return (
            self.collection.find_one(
                {"fecha_corte": {"$gte": fecha_desde, "$lt": fecha_hasta}},
                {"_id": 1},
            )
            is not None
        )


def _primer_dia_mes_siguiente(mes: date) -> date:
    return date(mes.year + (mes.month == 12), (mes.month % 12) + 1, 1)
