from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import (
    EvolucionBalanceMetadata,
)
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import VariacionMetadata


class CorteDepositosAPlazos(BaseModel):
    fecha: date
    plazo_1_30: Decimal | None
    plazo_31_90: Decimal | None
    plazo_91_180: Decimal | None
    plazo_181_360: Decimal | None
    plazo_mas_361: Decimal | None
    cuentas_sin_saldo: list[str]


class CorteEvolucionDepositosAPlazos(CorteDepositosAPlazos):
    depositos_plazo: Decimal | None
    parcial: bool = False


class CorteVariacionDepositosAPlazos(CorteDepositosAPlazos):
    fecha_comparacion: date


class EvolucionDepositosAPlazosResponse(EvolucionBalanceMetadata):
    datos: list[CorteEvolucionDepositosAPlazos]


class VariacionDepositosAPlazosResponse(VariacionMetadata):
    datos: list[CorteVariacionDepositosAPlazos]
