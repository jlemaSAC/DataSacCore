from decimal import Decimal

from app.modules.analytic.evolucion_cuentas.cartera_no_devenga.schemas import (
    EvolucionCarteraNoDevengaResponse,
    HistoricoCarteraNoDevengaResponse,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.service import EvolucionBalanceService
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.service import VariacionBalanceService

CUENTAS_NO_DEVENGA = (
    ("14", "cartera_total"),
    ("1499", "cartera_total"),
    ("1426", "consumo"),
    ("1434", "consumo_refinanciado"),
    ("1442", "consumo_reestructurado"),
    ("1427", "inmobiliario"),
    ("1428", "microcredito"),
    ("1436", "microcredito_refinanciado"),
    ("1444", "microcredito_reestructurado"),
)


class IndicadoresCarteraNoDevenga:
    cuentas = CUENTAS_NO_DEVENGA
    indicadores = tuple(cuenta for cuenta in CUENTAS_NO_DEVENGA if cuenta[0] != "1499")

    def valores_corte(self, saldos, fecha, ajustes):
        valores = super().valores_corte(saldos, fecha, ajustes)
        principal = saldos.get((fecha, "14"))
        ajuste = saldos.get((fecha, "1499"))
        valores["cartera_total"] = principal - (ajuste if ajuste is not None else Decimal("0")) if principal is not None else None
        return valores


class EvolucionCarteraNoDevengaService(IndicadoresCarteraNoDevenga, EvolucionBalanceService):
    response_model = EvolucionCarteraNoDevengaResponse


class HistoricoCarteraNoDevengaService(IndicadoresCarteraNoDevenga, VariacionBalanceService):
    response_model = HistoricoCarteraNoDevengaResponse
