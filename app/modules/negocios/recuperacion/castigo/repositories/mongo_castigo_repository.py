from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from bson import Decimal128
from pymongo.database import Database

from ..domain import (
    CorteCastigoNoDisponibleError,
    CorteDepositosCastigo,
    CortesDepositosCastigo,
    PrestamoCastigoInicio,
    normalizar_estado,
)

MongoDocument = dict[str, Any]
ESTADOS_INCLUIDOS = ["CASTIGADO", "CASTIGO", "JUDICIAL", "T", "J"]
TAMANO_LOTE = 500


class MongoCastigoRepository:
    """Lee el universo inicial y sus acumulados, incluyendo los cortes cancelados."""

    def __init__(self, mongo_db: Database[MongoDocument]) -> None:
        self.historico = mongo_db["SituacionCrediticia"]
        self.actual = mongo_db["SituacionCrediticiaActual"]

    def obtener_cortes(
        self,
        *,
        fecha_desde: date,
        fecha_hasta: date,
        fecha_actual: date,
        agencias: list[str],
        asesores: list[str],
        cargos: list[str],
        numeros_prestamo: list[str] | None = None,
    ) -> CortesDepositosCastigo:
        # El día anterior solo es base cuando pertenece al mismo mes.
        base = fecha_desde - timedelta(days=1) if fecha_desde.day > 1 else fecha_desde
        rango = {"fecha_corte": {
            "$gte": base.strftime("%Y%m%d"), "$lte": fecha_hasta.strftime("%Y%m%d"),
        }}
        fechas = {
            datetime.strptime(valor, "%Y%m%d").date()
            for valor in self.historico.distinct("fecha_corte", rango, maxTimeMS=60000)
        }
        fecha_sql = None
        if fecha_hasta == fecha_actual and fecha_actual not in fechas:
            ultimo = self.actual.find_one({}, {"_id": 0, "as_of": 1})
            if ultimo and _fecha_actual(ultimo.get("as_of")) == fecha_actual:
                fecha_sql = fecha_actual
                fechas.add(fecha_actual)
        fecha = base
        while fecha <= fecha_hasta:
            if fecha not in fechas:
                raise CorteCastigoNoDisponibleError(
                    f"No existe un corte de SituacionCrediticia para {fecha.isoformat()}; "
                    "no se puede calcular el depósito diario."
                )
            fecha += timedelta(days=1)

        es_inicio_actual = fecha_desde == fecha_sql
        coleccion_inicio = self.actual if es_inicio_actual else self.historico
        match_inicio: MongoDocument = (
            {} if es_inicio_actual else {"fecha_corte": fecha_desde.strftime("%Y%m%d")}
        )
        match_inicio["$or"] = [
            {"EstadoPrestamo": {"$in": ESTADOS_INCLUIDOS}},
            {"CodigoEstadoPrestamo": {"$in": ["T", "J"]}},
        ]
        if numeros_prestamo is not None:
            match_inicio["NumeroPrestamo"] = {"$in": numeros_prestamo}
        proyeccion = {campo: 1 for campo in (
            "NumeroPrestamo", "EstadoPrestamo", "CodigoEstadoPrestamo",
            "Agencia", "CodigoAsesor", "CodigoUsuario", "NombreAsesor", "CargoAsesor",
        )}
        proyeccion["_id"] = 0
        prestamos_por_numero: dict[str, PrestamoCastigoInicio] = {}
        for documento in coleccion_inicio.find(match_inicio, proyeccion).max_time_ms(60000):
            estado = normalizar_estado(
                documento.get("EstadoPrestamo") or documento.get("CodigoEstadoPrestamo")
            )
            agencia = _texto(documento.get("Agencia"))
            asesor = _texto(documento.get("NombreAsesor"))
            cargo = _texto(documento.get("CargoAsesor"))
            if estado not in {"CASTIGADO", "JUDICIAL"}:
                continue
            filtros = ((agencia, agencias), (asesor, asesores), (cargo, cargos))
            if any(valores and valor not in valores for valor, valores in filtros):
                continue
            numero = str(documento.get("NumeroPrestamo") or "").strip()
            if not numero:
                continue
            prestamo = PrestamoCastigoInicio(
                numero_prestamo=numero,
                estado=estado,
                agencia=agencia,
                codigo_asesor=str(
                    documento.get("CodigoUsuario") or documento.get("CodigoAsesor") or ""
                ).strip(),
                asesor=asesor,
                cargo=cargo,
            )
            anterior = prestamos_por_numero.get(numero)
            if anterior is not None and anterior != prestamo:
                raise CorteCastigoNoDisponibleError(
                    "El corte inicial contiene dimensiones contradictorias para un préstamo."
                )
            prestamos_por_numero[numero] = prestamo
        prestamos = list(prestamos_por_numero.values())
        if not prestamos:
            return CortesDepositosCastigo(prestamos=[], cortes=[])

        numeros = [prestamo.numero_prestamo for prestamo in prestamos]
        cortes = []
        estados_actuales = {}
        for offset in range(0, len(numeros), TAMANO_LOTE):
            lote = numeros[offset:offset + TAMANO_LOTE]
            match = {**rango, "NumeroPrestamo": {"$in": lote}}
            campos = {
                "_id": 0, "NumeroPrestamo": 1, "fecha_corte": 1,
                "DepositosMes": 1, "EstadoPrestamo": 1,
            }
            for documento in self.historico.find(match, campos).max_time_ms(60000):
                numero = str(documento["NumeroPrestamo"]).strip()
                fecha = datetime.strptime(documento["fecha_corte"], "%Y%m%d").date()
                if fecha == fecha_sql:
                    continue
                valor = documento.get("DepositosMes")
                if valor is None:
                    raise CorteCastigoNoDisponibleError(
                        f"El corte {fecha.isoformat()} no contiene DepositosMes "
                        "para todos los préstamos del universo inicial."
                    )
                try:
                    monto = valor.to_decimal() if isinstance(valor, Decimal128) else Decimal(str(valor))
                    if not monto.is_finite():
                        raise InvalidOperation
                except (InvalidOperation, ValueError) as exc:
                    raise CorteCastigoNoDisponibleError(
                        f"DepositosMes contiene un valor no válido en el corte {fecha.isoformat()}."
                    ) from exc
                cortes.append(CorteDepositosCastigo(
                    numero, fecha, monto, normalizar_estado(documento.get("EstadoPrestamo")),
                ))
            if fecha_sql:
                campos_actuales = {
                    "_id": 0, "NumeroPrestamo": 1,
                    "EstadoPrestamo": 1, "CodigoEstadoPrestamo": 1,
                }
                for documento in self.actual.find(
                    {"NumeroPrestamo": {"$in": lote}}, campos_actuales,
                ).max_time_ms(60000):
                    estados_actuales[str(documento["NumeroPrestamo"]).strip()] = normalizar_estado(
                        documento.get("EstadoPrestamo") or documento.get("CodigoEstadoPrestamo")
                    )
        return CortesDepositosCastigo(prestamos, cortes, fecha_sql, estados_actuales)


def _texto(valor: Any) -> str:
    return str(valor or "").strip().upper()


def _fecha_actual(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        instante = valor.replace(tzinfo=valor.tzinfo or timezone.utc)
        return instante.astimezone(ZoneInfo("America/Guayaquil")).date()
    if isinstance(valor, date):
        return valor
    if valor:
        try:
            return _fecha_actual(datetime.fromisoformat(str(valor).replace("Z", "+00:00")))
        except ValueError:
            return None
    return None
