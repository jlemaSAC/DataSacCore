from fastapi import APIRouter, Depends

from app.modules.analytic.indicadores_financieros.rentabilidad.dependencies import (
    get_rentabilidad_service,
)
from app.modules.analytic.indicadores_financieros.rentabilidad.schemas import (
    InputRentabilidad,
    RentabilidadResponse,
)
from app.modules.analytic.indicadores_financieros.rentabilidad.service import (
    IndicadoresRentabilidadService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(tags=["Analytic Sac - Indicadores Financieros"])


@router.post(
    "/indicadores-financieros/rentabilidad",
    response_model=RentabilidadResponse,
    summary="Calcular indicadores de rentabilidad con saldos contables neteados",
)
def rentabilidad(
    body: InputRentabilidad,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: IndicadoresRentabilidadService = Depends(get_rentabilidad_service),
) -> RentabilidadResponse:
    return service.calcular_rentabilidad(
        input_data=body,
        auth_context=auth_context,
    )
