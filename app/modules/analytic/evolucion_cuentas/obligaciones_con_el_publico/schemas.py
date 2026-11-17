from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import (
    EvolucionBalanceMetadata,
)
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import VariacionMetadata


class CorteObligacionesConElPublico(BaseModel):
    fecha: date
    depositos_plazo: Decimal | None
    depositos_vista: Decimal | None
    depositos_restringidos: Decimal | None
    cuentas_sin_saldo: list[str]


class CorteEvolucionObligacionesConElPublico(CorteObligacionesConElPublico):
    parcial: bool = False


class CorteHistoricoObligacionesConElPublico(CorteObligacionesConElPublico):
    fecha_comparacion: date


class EvolucionObligacionesConElPublicoResponse(EvolucionBalanceMetadata):
    datos: list[CorteEvolucionObligacionesConElPublico]


class HistoricoObligacionesConElPublicoResponse(VariacionMetadata):
    datos: list[CorteHistoricoObligacionesConElPublico]
