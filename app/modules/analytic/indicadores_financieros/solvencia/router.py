from fastapi import APIRouter, Depends

from app.modules.analytic.indicadores_financieros.solvencia.dependencies import (
    get_solvencia_service,
)
from app.modules.analytic.indicadores_financieros.solvencia.schemas import (
    InputSolvencia,
    InputSolvenciaHistorico,
    SolvenciaHistoricoResponse,
    SolvenciaResponse,
)
from app.modules.analytic.indicadores_financieros.solvencia.service import (
    IndicadoresFinancierosService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(tags=["Analytic Sac - Indicadores Financieros"])


@router.post(
    "/indicadores-financieros/solvencia",
    response_model=SolvenciaResponse,
    summary="Calcular indicador de solvencia con saldos contables neteados",
)
def solvencia(
    body: InputSolvencia,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresFinancierosService = Depends(get_solvencia_service),
) -> SolvenciaResponse:
    return service.calcular_solvencia(input_data=body, auth_context=auth_context)


@router.post(
    "/indicadores-financieros/solvencia/historico-mensual",
    response_model=SolvenciaHistoricoResponse,
    summary="Consultar indicadores de solvencia mensuales",
)
def solvencia_historico_mensual(
    body: InputSolvenciaHistorico,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresFinancierosService = Depends(get_solvencia_service),
) -> SolvenciaHistoricoResponse:
    return service.consultar_solvencia_historico_mensual(
        input_data=body,
        auth_context=auth_context,
    )


@router.post(
    "/indicadores-financieros/solvencia/historico-diario",
    response_model=SolvenciaHistoricoResponse,
    summary="Consultar indicadores de solvencia diarios",
)
def solvencia_historico_diario(
    body: InputSolvenciaHistorico,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresFinancierosService = Depends(get_solvencia_service),
) -> SolvenciaHistoricoResponse:
    return service.consultar_solvencia_historico_diario(
        input_data=body,
        auth_context=auth_context,
    )
