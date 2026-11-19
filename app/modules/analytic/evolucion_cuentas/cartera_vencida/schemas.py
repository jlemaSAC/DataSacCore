from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import (
    EvolucionBalanceMetadata,
)
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import VariacionMetadata


class CorteCarteraVencida(BaseModel):
    fecha: date
    cartera_total: Decimal | None
    consumo: Decimal | None
    inmobiliario: Decimal | None
    microcredito: Decimal | None
    consumo_refinanciado: Decimal | None
    consumo_reestructurado: Decimal | None
    microcredito_refinanciado: Decimal | None
    microcredito_reestructurado: Decimal | None
    cuentas_sin_saldo: list[str]


class CorteEvolucionCarteraVencida(CorteCarteraVencida):
    parcial: bool = False


class CorteHistoricoCarteraVencida(CorteCarteraVencida):
    fecha_comparacion: date


class EvolucionCarteraVencidaResponse(EvolucionBalanceMetadata):
    datos: list[CorteEvolucionCarteraVencida]


class HistoricoCarteraVencidaResponse(VariacionMetadata):
    datos: list[CorteHistoricoCarteraVencida]
