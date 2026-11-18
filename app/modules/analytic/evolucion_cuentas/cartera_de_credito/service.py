from decimal import Decimal

from app.modules.analytic.evolucion_cuentas.cartera_de_credito.schemas import (
    EvolucionCarteraResponse,
    HistoricoCarteraResponse,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.service import EvolucionBalanceService
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.service import VariacionBalanceService


# La cartera total corresponde a la cuenta 14 menos la cuenta 1499.
CUENTAS_POR_CARTERA = {
    "cartera_total": ("14","1499"),
    "consumo": ("1402", "1410", "1408","1418", "1426", "1434", "1442", "1450", "1458", "1466", ),
    "inmobiliario": ("1403", "1411", "1419", "1427", "1435", "1443", "1451", "1459", "1467",   ),
    "microcredito": ("1404", "1412", "1420", "1428", "1436", "1444", "1452", "1460", "1468",   ),
    "productivo": ("1401", "1409", "1417", "1425", "1433", "1441", "1449", "1457", "1465"),
}


class IndicadoresCartera:
    cuentas = tuple((codigo, campo) for campo, codigos in CUENTAS_POR_CARTERA.items() for codigo in codigos)
    indicadores = (
        ("14", "cartera_total"),
        ("consumo", "consumo"),
        ("inmobiliario", "inmobiliario"),
        ("microcredito", "microcredito"),
        ("productivo", "productivo"),
    )

    def valores_corte(self, saldos, fecha, ajustes):
        indicadores = {}
        for campo, codigos in CUENTAS_POR_CARTERA.items():
            if campo == "cartera_total":
                saldo = saldos.get((fecha, "14"))
                ajuste = saldos.get((fecha, "1499"))
                indicadores[campo] = saldo - (ajuste if ajuste is not None else Decimal("0.00")) if saldo is not None else None
                continue
            presentes = []
            for codigo in codigos:
                importe = saldos.get((fecha, codigo))
                if importe is not None:
                    presentes.append(importe)
            # Como en la suma de Power BI, un componente ausente no aporta al total.
            indicadores[campo] = sum(presentes, Decimal("0.00")) if presentes else None
        return indicadores


class EvolucionCarteraService(IndicadoresCartera, EvolucionBalanceService):
    response_model = EvolucionCarteraResponse


class HistoricoCarteraService(IndicadoresCartera, VariacionBalanceService):
    response_model = HistoricoCarteraResponse
