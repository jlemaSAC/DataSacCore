from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.colocacion.resumen.dependencies import get_resumen_colocacion_service
from app.modules.negocios.colocacion.resumen.schemas import (
    DetalleResumenColocacionResponse,
    InputDetalleResumenColocacion,
    InputResumenColocacion,
    ResumenColocacionResponse,
)
from app.modules.negocios.colocacion.resumen.service import ResumenColocacionService


router = APIRouter(prefix="/colocacion", tags=["Negocios - Colocacion"])


@router.post(
    "/resumen",
    response_model=ResumenColocacionResponse,
    summary="Obtener resumen comparativo de colocación por agencia",
)
def obtener_resumen_colocacion(
    body: InputResumenColocacion,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ResumenColocacionService = Depends(get_resumen_colocacion_service),
) -> ResumenColocacionResponse:
    return service.obtener_resumen(input_data=body, auth_context=auth_context)


@router.post(
    "/resumen/detalle",
    response_model=DetalleResumenColocacionResponse,
    summary="Obtener operaciones de una fila del resumen de colocación",
)
def obtener_detalle_resumen_colocacion(
    body: InputDetalleResumenColocacion,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ResumenColocacionService = Depends(get_resumen_colocacion_service),
) -> DetalleResumenColocacionResponse:
    return service.obtener_detalle(input_data=body, auth_context=auth_context)
