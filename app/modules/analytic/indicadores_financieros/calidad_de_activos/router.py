from fastapi import APIRouter, Depends

from app.modules.analytic.indicadores_financieros.calidad_de_activos.dependencies import (
    get_calidad_de_activos_service,
)
from app.modules.analytic.indicadores_financieros.calidad_de_activos.schemas import (
    CalidadDeActivosResponse,
    InputCalidadDeActivos,
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
