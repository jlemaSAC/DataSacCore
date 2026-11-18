from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import (
    EvolucionBalanceMetadata,
)
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import VariacionMetadata


class CorteCarteraPorVencer(BaseModel):
    fecha: date
    cartera_total: Decimal | None
    consumo: Decimal | None
    inmobiliario: Decimal | None
    microcredito: Decimal | None
    productivo: Decimal | None
    consumo_refinanciado: Decimal | None
    consumo_reestructurado: Decimal | None
    microcredito_refinanciado: Decimal | None
    microcredito_reestructurado: Decimal | None
    cuentas_sin_saldo: list[str]


class CorteEvolucionCarteraPorVencer(CorteCarteraPorVencer):
    parcial: bool = False


class CorteHistoricoCarteraPorVencer(CorteCarteraPorVencer):
    fecha_comparacion: date


class EvolucionCarteraPorVencerResponse(EvolucionBalanceMetadata):
    datos: list[CorteEvolucionCarteraPorVencer]


class HistoricoCarteraPorVencerResponse(VariacionMetadata):
    datos: list[CorteHistoricoCarteraPorVencer]
