from app.modules.analytic.evolucion_cuentas.cartera_por_vencer.schemas import (
    EvolucionCarteraPorVencerResponse,
    HistoricoCarteraPorVencerResponse,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.service import EvolucionBalanceService
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.service import VariacionBalanceService

CUENTAS_POR_VENCER = (
    ("1402", "consumo"),
    ("1403", "inmobiliario"),
    ("1404", "microcredito"),
    ("1401", "productivo"),
)


class EvolucionCarteraPorVencerService(EvolucionBalanceService):
    cuentas = CUENTAS_POR_VENCER
    response_model = EvolucionCarteraPorVencerResponse


class HistoricoCarteraPorVencerService(VariacionBalanceService):
    cuentas = CUENTAS_POR_VENCER
    response_model = HistoricoCarteraPorVencerResponse
