from fastapi import APIRouter, Depends

from app.modules.analytic.indicadores_financieros.indicadores_de_eficiencia.dependencies import (
    get_indicadores_de_eficiencia_service,
)
from app.modules.analytic.indicadores_financieros.indicadores_de_eficiencia.schemas import (
    IndicadoresDeEficienciaHistoricoResponse,
    IndicadoresDeEficienciaResponse,
    InputIndicadoresDeEficiencia,
    InputIndicadoresDeEficienciaHistorico,
)
from app.modules.analytic.indicadores_financieros.indicadores_de_eficiencia.service import (
    IndicadoresDeEficienciaService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(tags=["Analytic Sac - Indicadores Financieros"])


@router.post(
    "/indicadores-financieros/indicadores-de-eficiencia",
    response_model=IndicadoresDeEficienciaResponse,
    summary="Calcular indicadores de eficiencia estimados con saldos contables neteados",
)
def indicadores_de_eficiencia(
    body: InputIndicadoresDeEficiencia,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresDeEficienciaService = Depends(get_indicadores_de_eficiencia_service),
) -> IndicadoresDeEficienciaResponse:
    return service.calcular_indicadores_de_eficiencia(
        input_data=body,
        auth_context=auth_context,
    )


@router.post(
    "/indicadores-financieros/indicadores-de-eficiencia/historico-mensual",
    response_model=IndicadoresDeEficienciaHistoricoResponse,
    summary="Consultar indicadores de eficiencia mensuales",
)
def indicadores_de_eficiencia_historico_mensual(
    body: InputIndicadoresDeEficienciaHistorico,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresDeEficienciaService = Depends(get_indicadores_de_eficiencia_service),
) -> IndicadoresDeEficienciaHistoricoResponse:
    return service.consultar_indicadores_de_eficiencia_historico_mensual(
        input_data=body,
        auth_context=auth_context,
    )


@router.post(
    "/indicadores-financieros/indicadores-de-eficiencia/historico-diario",
    response_model=IndicadoresDeEficienciaHistoricoResponse,
    summary="Consultar indicadores de eficiencia diarios",
)
def indicadores_de_eficiencia_historico_diario(
    body: InputIndicadoresDeEficienciaHistorico,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresDeEficienciaService = Depends(get_indicadores_de_eficiencia_service),
) -> IndicadoresDeEficienciaHistoricoResponse:
    return service.consultar_indicadores_de_eficiencia_historico_diario(
        input_data=body,
        auth_context=auth_context,
    )
