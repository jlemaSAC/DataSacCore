from fastapi import APIRouter, Depends

from app.modules.analytic.evolucion_cuentas.cartera_vencida.dependencies import (
    get_evolucion_cartera_vencida_service,
    get_historico_cartera_vencida_service,
)
from app.modules.analytic.evolucion_cuentas.cartera_vencida.schemas import (
    EvolucionCarteraVencidaResponse,
    HistoricoCarteraVencidaResponse,
)
from app.modules.analytic.evolucion_cuentas.cartera_vencida.service import (
    EvolucionCarteraVencidaService,
    HistoricoCarteraVencidaService,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import ConsultaEvolucionBalance
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import ConsultaVariacion
from app.modules.auth.dependencies import get_current_auth_context

router = APIRouter(
    tags=["Analytic Sac - Evolución de cuentas"],
    dependencies=[Depends(get_current_auth_context)],
)


@router.post("/evolucion-cartera-vencida", response_model=EvolucionCarteraVencidaResponse)
def consultar_evolucion_cartera_vencida(
    body: ConsultaEvolucionBalance,
    service: EvolucionCarteraVencidaService = Depends(get_evolucion_cartera_vencida_service),
):
    return service.consultar(body)


@router.post("/historico-cartera-vencida", response_model=HistoricoCarteraVencidaResponse, include_in_schema=False)
@router.post("/variacion-cartera-vencida", response_model=HistoricoCarteraVencidaResponse)
def consultar_historico_cartera_vencida(
    body: ConsultaVariacion,
    service: HistoricoCarteraVencidaService = Depends(get_historico_cartera_vencida_service),
):
    return service.consultar(body)
