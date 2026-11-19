from fastapi import APIRouter, Depends

from app.modules.analytic.evolucion_cuentas.balance_de_resultados.dependencies import (
    get_evolucion_resultados_service,
    get_variacion_resultados_service,
)
from app.modules.analytic.evolucion_cuentas.balance_de_resultados.schemas import (
    EvolucionResultadosResponse,
    VariacionResultadosResponse,
)
from app.modules.analytic.evolucion_cuentas.balance_de_resultados.service import (
    EvolucionResultadosService,
    VariacionResultadosService,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import ConsultaEvolucionBalance
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import ConsultaVariacion
from app.modules.auth.dependencies import get_current_auth_context

router = APIRouter(
    tags=["Analytic Sac - Evolución de cuentas"],
    dependencies=[Depends(get_current_auth_context)],
)


@router.post("/evolucion-balance-de-resultados", response_model=EvolucionResultadosResponse)
def consultar_evolucion_resultados(
    body: ConsultaEvolucionBalance,
    service: EvolucionResultadosService = Depends(get_evolucion_resultados_service),
):
    return service.consultar(body)


@router.post("/variacion-balance-de-resultados", response_model=VariacionResultadosResponse)
def consultar_variacion_resultados(
    body: ConsultaVariacion,
    service: VariacionResultadosService = Depends(get_variacion_resultados_service),
):
    return service.consultar(body)
