from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import (
    EvolucionBalanceMetadata,
)
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import VariacionMetadata


class CorteResultados(BaseModel):
    fecha: date
    gastos: Decimal | None
    ingresos: Decimal | None
    utilidad: Decimal | None
    cuentas_sin_saldo: list[str]


class CorteEvolucionResultados(CorteResultados):
    parcial: bool = False


class CorteVariacionResultados(CorteResultados):
    fecha_comparacion: date


class EvolucionResultadosResponse(EvolucionBalanceMetadata):
    datos: list[CorteEvolucionResultados]


class VariacionResultadosResponse(VariacionMetadata):
    datos: list[CorteVariacionResultados]
