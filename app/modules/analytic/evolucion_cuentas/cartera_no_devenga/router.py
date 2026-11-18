from fastapi import APIRouter, Depends

from app.modules.analytic.evolucion_cuentas.cartera_no_devenga.dependencies import (
    get_evolucion_cartera_no_devenga_service,
    get_historico_cartera_no_devenga_service,
)
from app.modules.analytic.evolucion_cuentas.cartera_no_devenga.schemas import (
    EvolucionCarteraNoDevengaResponse,
    HistoricoCarteraNoDevengaResponse,
)
from app.modules.analytic.evolucion_cuentas.cartera_no_devenga.service import (
    EvolucionCarteraNoDevengaService,
    HistoricoCarteraNoDevengaService,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import ConsultaEvolucionBalance
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import ConsultaVariacion
from app.modules.auth.dependencies import get_current_auth_context

router = APIRouter(
    tags=["Analytic Sac - Evolución de cuentas"],
    dependencies=[Depends(get_current_auth_context)],
)


@router.post("/evolucion-cartera-no-devenga", response_model=EvolucionCarteraNoDevengaResponse)
def consultar_evolucion_cartera_no_devenga(
    body: ConsultaEvolucionBalance,
    service: EvolucionCarteraNoDevengaService = Depends(get_evolucion_cartera_no_devenga_service),
):
    return service.consultar(body)


@router.post("/variacion-cartera-no-devenga", response_model=HistoricoCarteraNoDevengaResponse)
def consultar_historico_cartera_no_devenga(
    body: ConsultaVariacion,
    service: HistoricoCarteraNoDevengaService = Depends(get_historico_cartera_no_devenga_service),
):
    return service.consultar(body)
