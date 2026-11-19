from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import (
    EvolucionBalanceMetadata,
)
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import VariacionMetadata


class CorteCartera(BaseModel):
    fecha: date
    cartera_total: Decimal | None
    consumo: Decimal | None
    inmobiliario: Decimal | None
    microcredito: Decimal | None
    productivo: Decimal | None
    cuentas_sin_saldo: list[str]


class CorteEvolucionCartera(CorteCartera):
    parcial: bool = False


class CorteHistoricoCartera(CorteCartera):
    fecha_comparacion: date


class EvolucionCarteraResponse(EvolucionBalanceMetadata):
    datos: list[CorteEvolucionCartera]


class HistoricoCarteraResponse(VariacionMetadata):
    datos: list[CorteHistoricoCartera]
