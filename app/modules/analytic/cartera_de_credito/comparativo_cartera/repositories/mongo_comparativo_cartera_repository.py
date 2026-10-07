from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from app.modules.analytic.cartera_de_credito.comparativo_cartera.domain import (
    TotalesCartera,
)


MongoDocument = dict[str, Any]
VALORES_DIFERIDO_TRUE: tuple[Any, ...] = (
    True,
    1,
    "1",
    "SI",
    "SÍ",
    "S",
    "TRUE",
    "DIFERIDO",
)


def _numero(campo: str) -> dict[str, Any]:
    return {
        "$convert": {
            "input": f"${campo}",
            "to": "double",
            "onError": 0,
            "onNull": 0,
        }
    }


def _provision_requerida(*, preferir_calculada: bool) -> dict[str, Any]:
    if not preferir_calculada:
        return _numero("ProvisionRequerida")

    provision_calculada = _numero("ProvisionRequeridaCalculada")
    return {
        "$cond": [
            {"$gt": [provision_calculada, 0]},
            provision_calculada,
            _numero("ProvisionRequerida"),
        ]
    }


class MongoComparativoCarteraRepository:
    historico_collection_name = "SituacionCrediticia"
    actual_collection_name = "SituacionCrediticiaActual"

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.historico: Collection[MongoDocument] = mongo_db[
            self.historico_collection_name
        ]
        self.actual: Collection[MongoDocument] = mongo_db[self.actual_collection_name]

    def obtener_historico(
        self,
        fechas: Iterable[date],
        agencias: list[str],
        filtrar_diferidos: bool | None,
    ) -> dict[date, TotalesCartera]:
        fechas_unicas = sorted({fecha.strftime("%Y%m%d") for fecha in fechas})
        if not fechas_unicas:
            return {}

        match = self._construir_match(
            agencias=agencias,
            filtrar_diferidos=filtrar_diferidos,
            historico=True,
        )
        match["fecha_corte"] = {"$in": fechas_unicas}
        rows = self.historico.aggregate(
            self._pipeline(match, "$fecha_corte"),
            hint="fecha_corte_1_estado_prestamo_1",
            allowDiskUse=True,
        )
        return self._mapear(rows)

    def obtener_actual(
        self,
        fecha_corte: date,
        agencias: list[str],
        filtrar_diferidos: bool | None,
    ) -> TotalesCartera | None:
        match = self._construir_match(
            agencias=agencias,
            filtrar_diferidos=filtrar_diferidos,
            historico=False,
        )
        rows = self.actual.aggregate(
            self._pipeline(
                match,
                {"$literal": fecha_corte.strftime("%Y%m%d")},
                preferir_provision_calculada=False,
            )
        )
        return next(iter(self._mapear(rows).values()), None)

    def obtener_por_agencia(
        self,
        fecha_corte: date,
        filtrar_diferidos: bool | None,
        *,
        actual: bool,
    ) -> dict[str, TotalesCartera]:
        """Obtiene los indicadores de cada agencia sin aplicar el filtro de agencias."""
        collection = self.actual if actual else self.historico
        match = self._construir_match(
            agencias=[],
            filtrar_diferidos=filtrar_diferidos,
            historico=not actual,
        )
        fecha_formateada = fecha_corte.strftime("%Y%m%d")
        if not actual:
            match["fecha_corte"] = fecha_formateada
        pipeline = self._pipeline_por_agencia(
            match,
            preferir_provision_calculada=not actual,
        )
        rows = collection.aggregate(
            pipeline,
            **(
                {"hint": "fecha_corte_1_estado_prestamo_1", "allowDiskUse": True}
                if not actual
                else {}
            ),
        )
        return self._mapear_por_agencia(rows, fecha_corte)

    @staticmethod
    def _construir_match(
        *,
        agencias: list[str],
        filtrar_diferidos: bool | None,
        historico: bool,
    ) -> MongoDocument:
        match: MongoDocument = {"EstadoPrestamo": {"$ne": "CANCELADO"}}
        if agencias:
            match["Agencia"] = {"$in": agencias}

        if filtrar_diferidos is not None:
            if historico:
                operador = "$in" if filtrar_diferidos else "$nin"
                match["ESDIFERIDO"] = {operador: list(VALORES_DIFERIDO_TRUE)}
            else:
                match["EsDiferido"] = filtrar_diferidos
        return match

    @staticmethod
    def _pipeline(
        match: MongoDocument,
        fecha_corte: str | MongoDocument,
        *,
        preferir_provision_calculada: bool = True,
    ) -> list[MongoDocument]:
        return [
            {"$match": match},
            {
                "$project": {
                    "fecha_corte": fecha_corte,
                    "saldo_capital": _numero("SaldoCapital"),
                    "capital_vigente": _numero("CapitalVigente"),
                    "capital_no_devenga": _numero("CapitalNoDevenga"),
                    "capital_vencido": _numero("CapitalVencido"),
                    "provision_requerida": _provision_requerida(
                        preferir_calculada=preferir_provision_calculada
                    ),
                }
            },
            {
                "$group": {
                    "_id": "$fecha_corte",
                    "operaciones": {"$sum": 1},
                    "saldo_capital": {"$sum": "$saldo_capital"},
                    "capital_vigente": {"$sum": "$capital_vigente"},
                    "capital_no_devenga": {"$sum": "$capital_no_devenga"},
                    "capital_vencido": {"$sum": "$capital_vencido"},
                    "provision_requerida": {"$sum": "$provision_requerida"},
                }
            },
        ]

    @staticmethod
    def _pipeline_por_agencia(
        match: MongoDocument,
        *,
        preferir_provision_calculada: bool,
    ) -> list[MongoDocument]:
        return [
            {"$match": match},
            {
                "$project": {
                    "agencia": "$Agencia",
                    "saldo_capital": _numero("SaldoCapital"),
                    "capital_no_devenga": _numero("CapitalNoDevenga"),
                    "capital_vencido": _numero("CapitalVencido"),
                    "provision_requerida": _provision_requerida(
                        preferir_calculada=preferir_provision_calculada
                    ),
                }
            },
            {
                "$group": {
                    "_id": "$agencia",
                    "operaciones": {"$sum": 1},
                    "saldo_capital": {"$sum": "$saldo_capital"},
                    "capital_no_devenga": {"$sum": "$capital_no_devenga"},
                    "capital_vencido": {"$sum": "$capital_vencido"},
                    "provision_requerida": {"$sum": "$provision_requerida"},
                }
            },
            {"$sort": {"_id": 1}},
        ]

    @staticmethod
    def _mapear_por_agencia(
        rows: Iterable[MongoDocument], fecha_corte: date
    ) -> dict[str, TotalesCartera]:
        resultado: dict[str, TotalesCartera] = {}
        for row in rows:
            agencia = str(row.get("_id") or "").strip()
            if not agencia:
                continue
            resultado[agencia] = TotalesCartera(
                fecha_corte=fecha_corte,
                operaciones=int(row.get("operaciones") or 0),
                saldo_capital=float(row.get("saldo_capital") or 0),
                capital_vigente=0.0,
                capital_no_devenga=float(row.get("capital_no_devenga") or 0),
                capital_vencido=float(row.get("capital_vencido") or 0),
                provision_requerida=float(row.get("provision_requerida") or 0),
            )
        return resultado

    @staticmethod
    def _mapear(rows: Iterable[MongoDocument]) -> dict[date, TotalesCartera]:
        resultado: dict[date, TotalesCartera] = {}
        for row in rows:
            fecha_corte = datetime.strptime(str(row["_id"]), "%Y%m%d").date()
            resultado[fecha_corte] = TotalesCartera(
                fecha_corte=fecha_corte,
                operaciones=int(row.get("operaciones") or 0),
                saldo_capital=float(row.get("saldo_capital") or 0),
                capital_vigente=float(row.get("capital_vigente") or 0),
                capital_no_devenga=float(row.get("capital_no_devenga") or 0),
                capital_vencido=float(row.get("capital_vencido") or 0),
                provision_requerida=float(row.get("provision_requerida") or 0),
            )
        return resultado
