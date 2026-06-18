from fastapi import APIRouter, Depends

from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.dependencies import (
    get_indicadores_de_liquidez_service,
)
from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.schemas import (
    IndicadoresDeLiquidezResponse,
    InputIndicadoresDeLiquidez,
)
from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.service import (
    IndicadoresDeLiquidezService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(tags=["Analytic Sac - Indicadores Financieros"])


@router.post(
    "/indicadores-financieros/indicadores-de-liquidez",
    response_model=IndicadoresDeLiquidezResponse,
    summary="Calcular indicadores de liquidez con saldos contables neteados",
)
def indicadores_de_liquidez(
    body: InputIndicadoresDeLiquidez,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresDeLiquidezService = Depends(get_indicadores_de_liquidez_service),
) -> IndicadoresDeLiquidezResponse:
    return service.calcular_indicadores_de_liquidez(
        input_data=body,
        auth_context=auth_context,
    )
