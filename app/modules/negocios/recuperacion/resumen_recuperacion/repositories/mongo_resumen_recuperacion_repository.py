from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from bson.decimal128 import Decimal128
from pymongo.database import Database

from app.modules.negocios.recuperacion.resumen_recuperacion.constants import TIPOS_COBRO
from app.modules.negocios.recuperacion.resumen_recuperacion.domain import RecuperacionDiaria


class MongoResumenRecuperacionRepository:
    """Materializa solo sumas diarias; nunca movimientos o contexto de préstamos."""

    def __init__(self, mongo_db: Database) -> None:
        self.historico = mongo_db["RecuperacionCrediticia"]
        self.actual = mongo_db["RecuperacionCrediticiaActual"]

    def obtener_diario(
        self,
        rangos: list[tuple[date, date]],
        fecha_actual: date,
        agencias: list[str],
    ) -> list[RecuperacionDiaria]:
        ayer = fecha_actual - timedelta(days=1)
        historicos = _unir_rangos([
            (inicio, min(fin, ayer)) for inicio, fin in rangos if inicio <= ayer
        ])
        consultas = []
        if historicos:
            consultas.append((self.historico, historicos))
        if any(inicio <= fecha_actual <= fin for inicio, fin in rangos):
            consultas.append((self.actual, [(fecha_actual, fecha_actual)]))

        dias: list[RecuperacionDiaria] = []
        for collection, intervalos in consultas:
            pipeline = self.construir_pipeline(intervalos, agencias)
            for fila in collection.aggregate(pipeline, maxTimeMS=15_000):
                dias.append(RecuperacionDiaria(
                    fecha=datetime.strptime(str(fila["_id"]), "%Y%m%d").date(),
                    montos={tipo: _decimal(fila.get(tipo, 0)) for tipo in TIPOS_COBRO},
                ))
        return sorted(dias, key=lambda dia: dia.fecha)

    @staticmethod
    def construir_pipeline(
        rangos: list[tuple[date, date]], agencias: list[str]
    ) -> list[dict[str, Any]]:
        filtros = [
            {"fecha_corte": {"$gte": inicio.strftime("%Y%m%d"), "$lte": fin.strftime("%Y%m%d")}}
            for inicio, fin in rangos
        ]
        normalizados: dict[str, Any] = {
            "numero_resumen": {"$trim": {"input": {"$convert": {
                "input": {"$ifNull": ["$NUMERO_PRESTAMO", "$NumeroPrestamo"]},
                "to": "string", "onError": "", "onNull": "",
            }}}}
        }
        validos: dict[str, Any] = {"numero_resumen": {"$ne": ""}}
        if agencias:
            # Conservar la normalización existente hasta validar los valores
            # reales de AGENCIA. El filtro de fecha sí usa el campo original.
            normalizados["agencia_resumen"] = {"$toUpper": {"$trim": {"input": {
                "$convert": {"input": "$AGENCIA", "to": "string", "onError": "", "onNull": ""}
            }}}}
            validos["agencia_resumen"] = {"$in": agencias}
        return [
            {"$match": filtros[0] if len(filtros) == 1 else {"$or": filtros}},
            {"$set": normalizados},
            {"$match": validos},
            {"$group": {
                "_id": "$fecha_corte",
                **{tipo: {"$sum": {"$convert": {
                    "input": "$" + tipo, "to": "decimal", "onError": 0, "onNull": 0,
                }}} for tipo in TIPOS_COBRO},
            }},
        ]


def _decimal(valor: Any) -> Decimal:
    return valor.to_decimal() if isinstance(valor, Decimal128) else Decimal(str(valor))


def _unir_rangos(rangos: list[tuple[date, date]]) -> list[tuple[date, date]]:
    unidos: list[tuple[date, date]] = []
    for inicio, fin in sorted(rangos):
        if unidos and inicio <= unidos[-1][1] + timedelta(days=1):
            unidos[-1] = (unidos[-1][0], max(unidos[-1][1], fin))
        else:
            unidos.append((inicio, fin))
    return unidos
