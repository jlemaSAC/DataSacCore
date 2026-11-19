from decimal import Decimal

from app.modules.analytic.evolucion_cuentas.cartera_por_vencer.schemas import (
    EvolucionCarteraPorVencerResponse,
    HistoricoCarteraPorVencerResponse,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.service import EvolucionBalanceService
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.service import VariacionBalanceService

CUENTAS_POR_VENCER = (
    ("14", "cartera_total"),
    ("1499", "cartera_total"),
    ("1402", "consumo"),
    ("1403", "inmobiliario"),
    ("1404", "microcredito"),
    ("1401", "productivo"),
    ("1410", "consumo_refinanciado"),
    ("1418", "consumo_reestructurado"),
    ("1412", "microcredito_refinanciado"),
    ("1420", "microcredito_reestructurado"),
)


class IndicadoresCarteraPorVencer:
    cuentas = CUENTAS_POR_VENCER
    indicadores = tuple(cuenta for cuenta in CUENTAS_POR_VENCER if cuenta[0] != "1499")

    def valores_corte(self, saldos, fecha, ajustes):
        valores = super().valores_corte(saldos, fecha, ajustes)
        principal = saldos.get((fecha, "14"))
        ajuste = saldos.get((fecha, "1499"))
        valores["cartera_total"] = principal - (ajuste if ajuste is not None else Decimal("0")) if principal is not None else None
        return valores


class EvolucionCarteraPorVencerService(IndicadoresCarteraPorVencer, EvolucionBalanceService):
    response_model = EvolucionCarteraPorVencerResponse


class HistoricoCarteraPorVencerService(IndicadoresCarteraPorVencer, VariacionBalanceService):
    response_model = HistoricoCarteraPorVencerResponse
