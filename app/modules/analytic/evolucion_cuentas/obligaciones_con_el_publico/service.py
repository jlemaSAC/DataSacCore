from app.modules.analytic.evolucion_cuentas.obligaciones_con_el_publico.schemas import (
    EvolucionObligacionesConElPublicoResponse,
    HistoricoObligacionesConElPublicoResponse,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.service import EvolucionBalanceService
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.service import VariacionBalanceService

CUENTAS_OBLIGACIONES = (
    ("2103", "depositos_plazo"),
    ("2101", "depositos_vista"),
    ("2105", "depositos_restringidos"),
    ("2106", "cuenta_2106"),
    ("21", "obligaciones_publico"),
)


class EvolucionObligacionesConElPublicoService(EvolucionBalanceService):
    cuentas = CUENTAS_OBLIGACIONES
    response_model = EvolucionObligacionesConElPublicoResponse


class HistoricoObligacionesConElPublicoService(VariacionBalanceService):
    cuentas = CUENTAS_OBLIGACIONES
    response_model = HistoricoObligacionesConElPublicoResponse
