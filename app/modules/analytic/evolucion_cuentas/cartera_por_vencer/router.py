from fastapi import APIRouter, Depends

from app.modules.analytic.evolucion_cuentas.cartera_por_vencer.dependencies import (
    get_evolucion_cartera_por_vencer_service,
    get_historico_cartera_por_vencer_service,
)
from app.modules.analytic.evolucion_cuentas.cartera_por_vencer.schemas import (
    EvolucionCarteraPorVencerResponse,
    HistoricoCarteraPorVencerResponse,
)
from app.modules.analytic.evolucion_cuentas.cartera_por_vencer.service import (
    EvolucionCarteraPorVencerService,
    HistoricoCarteraPorVencerService,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import ConsultaEvolucionBalance
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import ConsultaVariacion
from app.modules.auth.dependencies import get_current_auth_context

router = APIRouter(
    tags=["Analytic Sac - Evolución de cuentas"],
    dependencies=[Depends(get_current_auth_context)],
)


@router.post("/evolucion-cartera-por-vencer", response_model=EvolucionCarteraPorVencerResponse)
def consultar_evolucion_cartera_por_vencer(
    body: ConsultaEvolucionBalance,
    service: EvolucionCarteraPorVencerService = Depends(get_evolucion_cartera_por_vencer_service),
):
    return service.consultar(body)


@router.post("/historico-cartera-por-vencer", response_model=HistoricoCarteraPorVencerResponse)
def consultar_historico_cartera_por_vencer(
    body: ConsultaVariacion,
    service: HistoricoCarteraPorVencerService = Depends(get_historico_cartera_por_vencer_service),
):
    return service.consultar(body)
