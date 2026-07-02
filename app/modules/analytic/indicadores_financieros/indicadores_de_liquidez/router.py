from fastapi import APIRouter, Depends

from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.dependencies import (
    get_indicadores_de_liquidez_service,
)
from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.schemas import (
    IndicadoresDeLiquidezHistoricoResponse,
    IndicadoresDeLiquidezResponse,
    InputIndicadoresDeLiquidez,
    InputIndicadoresDeLiquidezHistorico,
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


@router.post(
    "/indicadores-financieros/indicadores-de-liquidez/historico-mensual",
    response_model=IndicadoresDeLiquidezHistoricoResponse,
    summary="Consultar indicadores de liquidez mensuales con saldos contables neteados",
)
def indicadores_de_liquidez_historico(
    body: InputIndicadoresDeLiquidezHistorico,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresDeLiquidezService = Depends(get_indicadores_de_liquidez_service),
) -> IndicadoresDeLiquidezHistoricoResponse:
    return service.consultar_indicadores_de_liquidez_historico(
        input_data=body,
        auth_context=auth_context,
    )


@router.post(
    "/indicadores-financieros/indicadores-de-liquidez/historico-diario",
    response_model=IndicadoresDeLiquidezHistoricoResponse,
    summary="Consultar indicadores de liquidez diarios con saldos contables neteados",
)
def indicadores_de_liquidez_historico_diario(
    body: InputIndicadoresDeLiquidezHistorico,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresDeLiquidezService = Depends(get_indicadores_de_liquidez_service),
) -> IndicadoresDeLiquidezHistoricoResponse:
    return service.consultar_indicadores_de_liquidez_historico_diario(
        input_data=body,
        auth_context=auth_context,
    )
