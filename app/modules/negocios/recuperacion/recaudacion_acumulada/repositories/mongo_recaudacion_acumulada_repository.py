from datetime import date, datetime, timedelta
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from app.modules.negocios.recuperacion.recaudacion_acumulada.domain import (
    RecuperacionPrestamo,
)


MongoDocument = dict[str, Any]
COLECCION_RECUPERACION = "RecuperacionCrediticia"
COLECCION_RECUPERACION_ACTUAL = "RecuperacionCrediticiaActual"
COLECCION_SITUACION = "SituacionCrediticia"
COLECCION_SITUACION_ACTUAL = "SituacionCrediticiaActual"

PROYECCION_SITUACION = {
    "_id": 0,
    "NumeroPrestamo": 1,
    "Cliente": 1,
    "Nombres": 1,
    "Identificacion": 1,
    "Direccion": 1,
    "Telefonos": 1,
    "Provincia": 1,
    "Canton": 1,
    "Parroquia": 1,
    "Agencia": 1,
    "CodigoAsesor": 1,
    "NombreAsesor": 1,
    "EstadoPrestamo": 1,
    "CodigoEstadoPrestamo": 1,
    "Calificacion": 1,
    "DiasVencidos": 1,
    "SaldoCapital": 1,
    "ProvisionRequerida": 1,
    "ValorParaEstarAlDia": 1,
    "ValorHastaCuotaActual": 1,
    "ValorCancelarTotal": 1,
    "GastoCobranza": 1,
    "Plazo": 1,
    "G1_Identificacion": 1,
    "G1_Nombres": 1,
    "G1_Provincia": 1,
    "G1_Canton": 1,
    "G1_Parroquia": 1,
    "G1_Direccion": 1,
    "G1_Telefonos": 1,
    "G2_Identificacion": 1,
    "G2_Nombres": 1,
    "G2_Provincia": 1,
    "G2_Canton": 1,
    "G2_Parroquia": 1,
    "G2_Direccion": 1,
    "G2_Telefonos": 1,
}


class MongoRecaudacionAcumuladaRepository:
    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.situacion: Collection[MongoDocument] = mongo_db[COLECCION_SITUACION]
        self.situacion_actual: Collection[MongoDocument] = mongo_db[
            COLECCION_SITUACION_ACTUAL
        ]
        self.recuperacion: Collection[MongoDocument] = mongo_db[
            COLECCION_RECUPERACION
        ]
        self.recuperacion_actual: Collection[MongoDocument] = mongo_db[
            COLECCION_RECUPERACION_ACTUAL
        ]

    def existe_corte(self, fecha_corte: date, fecha_actual: date) -> bool:
        if fecha_corte == fecha_actual:
            return self.situacion_actual.find_one({}, {"_id": 1}) is not None
        return (
            self.situacion.find_one(
                {"fecha_corte": fecha_corte.strftime("%Y%m%d")}, {"_id": 1}
            )
            is not None
        )

    def obtener_corte_inicial(
        self,
        fecha_corte: date,
        numeros_prestamo: list[str],
    ) -> dict[str, MongoDocument]:
        if not numeros_prestamo:
            return {}
        filtro = {
            "fecha_corte": fecha_corte.strftime("%Y%m%d"),
            "NumeroPrestamo": {"$in": numeros_prestamo},
            "EstadoPrestamo": {"$nin": ["CANCELADO", "C"]},
        }
        return self._por_numero(self.situacion.find(filtro, PROYECCION_SITUACION))

    def obtener_corte_final(
        self,
        fecha_corte: date,
        fecha_actual: date,
        agencias: list[str],
        asesores: list[str],
    ) -> dict[str, MongoDocument]:
        filtro: MongoDocument = {"Agencia": {"$in": agencias}}
        if fecha_corte != fecha_actual:
            filtro["fecha_corte"] = fecha_corte.strftime("%Y%m%d")
        if asesores:
            filtro["$or"] = [
                {"NombreAsesor": {"$in": asesores}},
                {"CodigoAsesor": {"$in": asesores}},
            ]
        collection = (
            self.situacion_actual if fecha_corte == fecha_actual else self.situacion
        )
        return self._por_numero(collection.find(filtro, PROYECCION_SITUACION))

    def obtener_recuperaciones(
        self,
        fecha_inicio: date,
        fecha_fin: date,
        fecha_actual: date,
        numeros_prestamo: list[str],
    ) -> dict[str, RecuperacionPrestamo]:
        if not numeros_prestamo:
            return {}
        desde = fecha_inicio.strftime("%Y%m%d")
        hasta = fecha_fin.strftime("%Y%m%d")
        ayer = (fecha_actual - timedelta(days=1)).strftime("%Y%m%d")
        incluye_actual = fecha_inicio <= fecha_actual <= fecha_fin

        if fecha_inicio == fecha_actual:
            collection = self.recuperacion_actual
            pipeline = self._pipeline_recuperaciones(desde, hasta, numeros_prestamo)
        else:
            collection = self.recuperacion
            pipeline = self._pipeline_recuperaciones(
                desde, min(hasta, ayer), numeros_prestamo
            )
            if incluye_actual:
                pipeline.append(
                    {
                        "$unionWith": {
                            "coll": COLECCION_RECUPERACION_ACTUAL,
                            "pipeline": self._pipeline_recuperaciones(
                                hasta, hasta, numeros_prestamo
                            ),
                        }
                    }
                )

        pipeline.extend(
            [
                {
                    "$group": {
                        "_id": "$numero_prestamo",
                        "fecha_ultimo_pago": {"$max": "$fecha_pago"},
                        "total_recuperado": {"$sum": "$total_recuperado"},
                    }
                },
                {"$match": {"_id": {"$ne": ""}}},
            ]
        )
        resultado: dict[str, RecuperacionPrestamo] = {}
        for fila in collection.aggregate(pipeline, allowDiskUse=True):
            numero = str(fila.get("_id") or "").strip()
            if not numero:
                continue
            resultado[numero] = RecuperacionPrestamo(
                numero_prestamo=numero,
                fecha_ultimo_pago=_a_date(fila.get("fecha_ultimo_pago")),
                total_recuperado=float(fila.get("total_recuperado") or 0),
            )
        return resultado

    @staticmethod
    def _pipeline_recuperaciones(
        desde: str,
        hasta: str,
        numeros_prestamo: list[str],
    ) -> list[MongoDocument]:
        return [
            {
                "$match": {
                    "fecha_corte": {"$gte": desde, "$lte": hasta},
                    "$or": [
                        {"NUMERO_PRESTAMO": {"$in": numeros_prestamo}},
                        {"NumeroPrestamo": {"$in": numeros_prestamo}},
                    ],
                }
            },
            {
                "$project": {
                    "numero_prestamo": {
                        "$trim": {
                            "input": {
                                "$convert": {
                                    "input": {
                                        "$ifNull": [
                                            "$NUMERO_PRESTAMO",
                                            "$NumeroPrestamo",
                                        ]
                                    },
                                    "to": "string",
                                    "onError": "",
                                    "onNull": "",
                                }
                            }
                        }
                    },
                    "fecha_pago": {"$ifNull": ["$FECHA_COBRO", "$fecha_corte"]},
                    "total_recuperado": {
                        "$convert": {
                            "input": "$TOTAL_RECUPERADO",
                            "to": "double",
                            "onError": 0,
                            "onNull": 0,
                        }
                    },
                }
            },
        ]

    @staticmethod
    def _por_numero(documentos) -> dict[str, MongoDocument]:
        resultado: dict[str, MongoDocument] = {}
        for documento in documentos:
            numero = str(documento.get("NumeroPrestamo") or "").strip()
            if numero:
                resultado[numero] = documento
        return resultado


def _a_date(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()[:10]
    for formato in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return date.fromisoformat(texto) if formato == "%Y-%m-%d" else date(
                int(texto[:4]), int(texto[4:6]), int(texto[6:8])
            )
        except (TypeError, ValueError):
            continue
    return None
