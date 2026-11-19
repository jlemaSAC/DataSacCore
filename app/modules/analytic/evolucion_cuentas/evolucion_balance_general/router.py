from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.dependencies import get_evolucion_balance_service
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import ConsultaEvolucionBalance, EvolucionBalanceResponse
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.service import EvolucionBalanceService

router = APIRouter(tags=["Analytic Sac - Evolución de cuentas"])


@router.post("/evolucion-balance-general", response_model=EvolucionBalanceResponse,
             summary="Evolución mensual o diaria de Activos, Pasivos y Patrimonio")
def consultar_evolucion_balance(
    body: ConsultaEvolucionBalance,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: EvolucionBalanceService = Depends(get_evolucion_balance_service),
) -> EvolucionBalanceResponse:
    return service.consultar(body)
