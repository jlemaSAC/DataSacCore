from fastapi import APIRouter, Depends
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.dependencies import get_variacion_balance_service
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import ConsultaVariacion, VariacionResponse
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.service import VariacionBalanceService

router = APIRouter(tags=['Analytic Sac - Evolución de cuentas'])


@router.post('/variacion-balance-general', response_model=VariacionResponse)
def consultar_variacion(body: ConsultaVariacion, auth_context: AuthContext = Depends(get_current_auth_context), service: VariacionBalanceService = Depends(get_variacion_balance_service)) -> VariacionResponse:
    return service.consultar(body)
