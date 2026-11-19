from fastapi import APIRouter, Depends

from app.modules.analytic.evolucion_cuentas.depositos_a_plazos.dependencies import (
    get_evolucion_depositos_a_plazos_service,
    get_variacion_depositos_a_plazos_service,
)
from app.modules.analytic.evolucion_cuentas.depositos_a_plazos.schemas import (
    EvolucionDepositosAPlazosResponse,
    VariacionDepositosAPlazosResponse,
)
from app.modules.analytic.evolucion_cuentas.depositos_a_plazos.service import (
    EvolucionDepositosAPlazosService,
    VariacionDepositosAPlazosService,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import ConsultaEvolucionBalance
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import ConsultaVariacion
from app.modules.auth.dependencies import get_current_auth_context

router = APIRouter(
    tags=["Analytic Sac - Evolución de cuentas"],
    dependencies=[Depends(get_current_auth_context)],
)


@router.post("/evolucion-depositos-a-plazos", response_model=EvolucionDepositosAPlazosResponse)
def consultar_evolucion_depositos_a_plazos(
    body: ConsultaEvolucionBalance,
    service: EvolucionDepositosAPlazosService = Depends(get_evolucion_depositos_a_plazos_service),
):
    return service.consultar(body)


@router.post("/variacion-depositos-a-plazos", response_model=VariacionDepositosAPlazosResponse)
def consultar_variacion_depositos_a_plazos(
    body: ConsultaVariacion,
    service: VariacionDepositosAPlazosService = Depends(get_variacion_depositos_a_plazos_service),
):
    return service.consultar(body)
