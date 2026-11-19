from app.modules.analytic.evolucion_cuentas.depositos_a_plazos.schemas import (
    EvolucionDepositosAPlazosResponse,
    VariacionDepositosAPlazosResponse,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.service import EvolucionBalanceService
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.service import VariacionBalanceService

CUENTAS_DEPOSITOS_PLAZOS = (
    ("210305", "plazo_1_30"),
    ("210310", "plazo_31_90"),
    ("210315", "plazo_91_180"),
    ("210320", "plazo_181_360"),
    ("210325", "plazo_mas_361"),
)


class EvolucionDepositosAPlazosService(EvolucionBalanceService):
    cuentas = CUENTAS_DEPOSITOS_PLAZOS + (("2103", "depositos_plazo"),)
    response_model = EvolucionDepositosAPlazosResponse


class VariacionDepositosAPlazosService(VariacionBalanceService):
    cuentas = CUENTAS_DEPOSITOS_PLAZOS
    response_model = VariacionDepositosAPlazosResponse
