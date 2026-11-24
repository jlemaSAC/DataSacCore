from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext

from .dependencies import get_indicadores_inactividad_service
from .schemas import (
    IndicadoresInactividadRequest,
    IndicadoresInactividadResponse,
)
from .service import IndicadoresInactividadService


router = APIRouter(prefix="/cuentas/indicadores-de-inactividad", tags=["Negocios - Cuentas"])


@router.post("", response_model=IndicadoresInactividadResponse)
def consultar_indicadores(
    body: IndicadoresInactividadRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    servicio: IndicadoresInactividadService = Depends(get_indicadores_inactividad_service),
) -> IndicadoresInactividadResponse:
    return servicio.consultar(body, auth)
