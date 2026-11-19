from fastapi import APIRouter, Depends

from app.modules.analytic.evolucion_cuentas.cartera_de_credito.dependencies import (
    get_evolucion_cartera_service,
    get_historico_cartera_service,
)
from app.modules.analytic.evolucion_cuentas.cartera_de_credito.schemas import (
    EvolucionCarteraResponse,
    HistoricoCarteraResponse,
)
from app.modules.analytic.evolucion_cuentas.cartera_de_credito.service import (
    EvolucionCarteraService,
    HistoricoCarteraService,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import ConsultaEvolucionBalance
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import ConsultaVariacion
from app.modules.auth.dependencies import get_current_auth_context

router = APIRouter(
    tags=["Analytic Sac - Evolución de cuentas"],
    dependencies=[Depends(get_current_auth_context)],
)


@router.post("/evolucion-cartera-de-credito", response_model=EvolucionCarteraResponse)
def consultar_evolucion_cartera(
    body: ConsultaEvolucionBalance,
    service: EvolucionCarteraService = Depends(get_evolucion_cartera_service),
):
    return service.consultar(body)


@router.post("/variacion-cartera-de-credito", response_model=HistoricoCarteraResponse)
@router.post("/historico-cartera-de-credito", response_model=HistoricoCarteraResponse, include_in_schema=False)
def consultar_historico_cartera(
    body: ConsultaVariacion,
    service: HistoricoCarteraService = Depends(get_historico_cartera_service),
):
    return service.consultar(body)
