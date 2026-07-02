from fastapi import APIRouter, Depends

from app.modules.analytic.indicadores_financieros.calidad_de_activos.dependencies import (
    get_calidad_de_activos_service,
)
from app.modules.analytic.indicadores_financieros.calidad_de_activos.schemas import (
    CalidadDeActivosHistoricoResponse,
    CalidadDeActivosResponse,
    InputCalidadDeActivos,
    InputCalidadDeActivosHistorico,
)
from app.modules.analytic.indicadores_financieros.calidad_de_activos.service import (
    IndicadoresCalidadDeActivosService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(tags=["Analytic Sac - Indicadores Financieros"])


@router.post(
    "/indicadores-financieros/calidad-de-activos",
    response_model=CalidadDeActivosResponse,
    summary="Calcular indicadores de calidad de activos con saldos contables neteados",
)
def calidad_de_activos(
    body: InputCalidadDeActivos,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresCalidadDeActivosService = Depends(get_calidad_de_activos_service),
) -> CalidadDeActivosResponse:
    return service.calcular_calidad_de_activos(
        input_data=body,
        auth_context=auth_context,
    )


@router.post(
    "/indicadores-financieros/calidad-de-activos/historico-mensual",
    response_model=CalidadDeActivosHistoricoResponse,
    summary="Consultar indicadores de calidad de activos mensuales",
)
def calidad_de_activos_historico_mensual(
    body: InputCalidadDeActivosHistorico,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresCalidadDeActivosService = Depends(get_calidad_de_activos_service),
) -> CalidadDeActivosHistoricoResponse:
    return service.consultar_calidad_de_activos_historico_mensual(
        input_data=body,
        auth_context=auth_context,
    )


@router.post(
    "/indicadores-financieros/calidad-de-activos/historico-diario",
    response_model=CalidadDeActivosHistoricoResponse,
    summary="Consultar indicadores de calidad de activos diarios",
)
def calidad_de_activos_historico_diario(
    body: InputCalidadDeActivosHistorico,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresCalidadDeActivosService = Depends(get_calidad_de_activos_service),
) -> CalidadDeActivosHistoricoResponse:
    return service.consultar_calidad_de_activos_historico_diario(
        input_data=body,
        auth_context=auth_context,
    )
