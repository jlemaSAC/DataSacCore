from decimal import Decimal

from app.modules.analytic.evolucion_cuentas.cartera_vencida.schemas import (
    EvolucionCarteraVencidaResponse,
    HistoricoCarteraVencidaResponse,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.service import EvolucionBalanceService
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.service import VariacionBalanceService

CUENTAS_VENCIDA = (
    ("14", "cartera_total"),
    ("1499", "cartera_total"),
    ("1450", "consumo"),
    ("1458", "consumo_refinanciado"),
    ("1466", "consumo_reestructurado"),
    ("1451", "inmobiliario"),
    ("1452", "microcredito"),
    ("1460", "microcredito_refinanciado"),
    ("1468", "microcredito_reestructurado"),
)


class IndicadoresCarteraVencida:
    cuentas = CUENTAS_VENCIDA
    indicadores = tuple(cuenta for cuenta in CUENTAS_VENCIDA if cuenta[0] != "1499")

    def valores_corte(self, saldos, fecha, ajustes):
        valores = super().valores_corte(saldos, fecha, ajustes)
        principal = saldos.get((fecha, "14"))
        ajuste = saldos.get((fecha, "1499"))
        valores["cartera_total"] = principal - (ajuste if ajuste is not None else Decimal("0")) if principal is not None else None
        return valores


class EvolucionCarteraVencidaService(IndicadoresCarteraVencida, EvolucionBalanceService):
    response_model = EvolucionCarteraVencidaResponse


class HistoricoCarteraVencidaService(IndicadoresCarteraVencida, VariacionBalanceService):
    response_model = HistoricoCarteraVencidaResponse
