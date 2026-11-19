from app.modules.analytic.evolucion_cuentas.balance_de_resultados.schemas import (
    EvolucionResultadosResponse,
    VariacionResultadosResponse,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.service import (
    EvolucionBalanceService,
)
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.service import (
    VariacionBalanceService,
)


class IndicadoresResultados:
    cuentas = (("4", "gastos"), ("5", "ingresos"))

    def completar_corte(self, corte: dict) -> None:
        ingresos, gastos = corte["ingresos"], corte["gastos"]
        corte["utilidad"] = ingresos - gastos if ingresos is not None and gastos is not None else None


class EvolucionResultadosService(IndicadoresResultados, EvolucionBalanceService):
    response_model = EvolucionResultadosResponse


class VariacionResultadosService(IndicadoresResultados, VariacionBalanceService):
    response_model = VariacionResultadosResponse
