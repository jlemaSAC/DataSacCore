from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from bson import Decimal128
from pymongo.database import Database

from ..domain import CorteAsesor, CortesControlCartera

MongoDocument = dict[str, Any]


def _texto(*campos: str, defecto: str = "") -> Any:
    valor: Any = defecto
    for campo in reversed(campos):
        texto = {
            "$trim": {"input": {"$convert": {
                "input": f"${campo}", "to": "string", "onError": "", "onNull": "",
            }}}
        }
        valor = {"$cond": [{"$ne": [texto, ""]}, texto, valor]}
    return valor


def _numero(campo: str) -> MongoDocument:
    return {"$convert": {"input": f"${campo}", "to": "decimal", "onError": 0, "onNull": 0}}


def _decimal(value: Any) -> Decimal:
    return value.to_decimal() if isinstance(value, Decimal128) else Decimal(str(value or 0))


class MongoControlDiarioCarteraRepository:
    """Agrega un rango mensual en el servidor y devuelve solo cortes por asesor/agencia."""

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.historico = mongo_db["SituacionCrediticia"]
        self.actual = mongo_db["SituacionCrediticiaActual"]

    def obtener_cortes(
        self,
        *,
        desde: date,
        hasta: date,
        agencia: str | None,
        filtrar_diferidos: bool | None,
    ) -> CortesControlCartera:
        rango = {"fecha_corte": {
            "$gte": desde.strftime("%Y%m%d"), "$lte": hasta.strftime("%Y%m%d"),
        }}
        # distinct usa el índice de fecha y distingue un corte sin coincidencias de un corte ausente.
        fechas = {
            datetime.strptime(valor, "%Y%m%d").date()
            for valor in self.historico.distinct("fecha_corte", rango, maxTimeMS=60000)
        }
        match: MongoDocument = {**rango, "EstadoPrestamo": {"$ne": "CANCELADO"}}
        if agencia:
            match["Agencia"] = agencia
        filas = list(self.historico.aggregate(
            self._pipeline(match, filtrar_diferidos, actual=False),
            hint="fecha_corte_1_estado_prestamo_1",
            allowDiskUse=True,
            maxTimeMS=60000,
        ))
        # El snapshot actual solo completa su fecha real; nunca se copia a otros días.
        ultimo = self.actual.find_one(
            {"as_of": {"$exists": True}},
            {"_id": 0, "as_of": 1},
            sort=[("as_of", -1)],
        )
        fecha_actual = _fecha_actual(ultimo.get("as_of")) if ultimo else None
        if fecha_actual and desde <= fecha_actual <= hasta and fecha_actual not in fechas:
            match_actual: MongoDocument = {"EstadoPrestamo": {"$ne": "CANCELADO"}}
            if agencia:
                match_actual["Agencia"] = agencia
            filas.extend(self.actual.aggregate(
                self._pipeline(match_actual, filtrar_diferidos, actual=True, fecha=fecha_actual),
                allowDiskUse=True, maxTimeMS=60000,
            ))
            fechas.add(fecha_actual)
        return CortesControlCartera(
            fechas=fechas,
            asesores=[CorteAsesor(
                fecha=datetime.strptime(row["_id"]["fecha"], "%Y%m%d").date(),
                codigo_asesor=row["_id"]["codigo"],
                agencia=row["_id"]["agencia"],
                nombre_asesor=row["nombre"],
                cargo=row["cargo"],
                saldo_capital=_decimal(row["saldo_capital"]),
                cartera_improductiva=_decimal(row["cartera_improductiva"]),
                provisiones=_decimal(row["provisiones"]),
            ) for row in filas],
        )

    @staticmethod
    def _pipeline(
        match: MongoDocument,
        diferidos: bool | None,
        *,
        actual: bool,
        fecha: date | None = None,
    ) -> list[MongoDocument]:
        pipeline: list[MongoDocument] = [{"$match": match}]
        if diferidos is not None:
            es_diferido = {"$in": [
                {"$toUpper": _texto("ESDIFERIDO", "EsDiferido", "Diferido")},
                ["SI", "SÍ", "S", "TRUE", "1", "DIFERIDO"],
            ]}
            pipeline.append({"$match": {"$expr": {"$eq": [es_diferido, diferidos]}}})
        provision: Any = _numero("ProvisionRequerida")
        if not actual:
            calculada = _numero("ProvisionRequeridaCalculada")
            provision = {"$cond": [{"$gt": [calculada, 0]}, calculada, provision]}
        pipeline.extend([
            {"$project": {
                "_id": 0,
                "fecha": {"$literal": fecha.strftime("%Y%m%d")} if fecha else "$fecha_corte",
                "codigo": _texto("CodigoUsuario", "CodigoAsesor", defecto="SIN ASESOR"),
                "nombre": _texto("NombreAsesor", "NombreCompleto", defecto="SIN NOMBRE"),
                "cargo": _texto("CargoAsesor", defecto="SIN CARGO"),
                "agencia": _texto("Agencia", defecto="SIN AGENCIA"),
                "saldo_capital": _numero("SaldoCapital"),
                "cartera_improductiva": {"$add": [
                    _numero("CapitalNoDevenga"), _numero("CapitalVencido"),
                ]},
                "provisiones": provision,
            }},
            {"$group": {
                "_id": {"fecha": "$fecha", "codigo": "$codigo", "agencia": "$agencia"},
                "nombre": {"$max": "$nombre"}, "cargo": {"$max": "$cargo"},
                "saldo_capital": {"$sum": "$saldo_capital"},
                "cartera_improductiva": {"$sum": "$cartera_improductiva"},
                "provisiones": {"$sum": "$provisiones"},
            }},
        ])
        return pipeline


def _fecha_actual(value: Any) -> date | None:
    if isinstance(value, datetime):
        instante = value.replace(tzinfo=value.tzinfo or timezone.utc)
        return instante.astimezone(ZoneInfo("America/Guayaquil")).date()
    if isinstance(value, date):
        return value
    if value:
        texto = str(value).strip()
        try:
            if len(texto) == 8 and texto.isdigit():
                return datetime.strptime(texto, "%Y%m%d").date()
            return _fecha_actual(datetime.fromisoformat(texto.replace("Z", "+00:00")))
        except ValueError:
            return None
    return None
