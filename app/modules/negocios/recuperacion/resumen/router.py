from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.recuperacion.resumen.dependencies import (
    get_detalle_resumen_recuperacion_service,
    get_resumen_recuperacion_service,
)
from app.modules.negocios.recuperacion.resumen.schemas import (
    DetalleResumenRecuperacionResponse,
    InputDetalleResumenRecuperacion,
    InputResumenRecuperacion,
    ResumenRecuperacionResponse,
)
from app.modules.negocios.recuperacion.resumen.service import ResumenRecuperacionService


router = APIRouter(prefix="/recuperacion", tags=["Negocios - Recuperacion"])


@router.post(
    "/resumen",
    response_model=ResumenRecuperacionResponse,
    summary="Obtener resumen comparativo de recuperación por agencia",
)
def obtener_resumen_recuperacion(
    body: InputResumenRecuperacion,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ResumenRecuperacionService = Depends(get_resumen_recuperacion_service),
) -> ResumenRecuperacionResponse:
    return service.obtener_resumen(input_data=body, auth_context=auth_context)


@router.post(
    "/resumen/detalle",
    response_model=DetalleResumenRecuperacionResponse,
    summary="Obtener detalle paginado de recuperación con estado operativo actual",
)
def obtener_detalle_resumen_recuperacion(
    body: InputDetalleResumenRecuperacion,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ResumenRecuperacionService = Depends(
        get_detalle_resumen_recuperacion_service
    ),
) -> DetalleResumenRecuperacionResponse:
    return service.obtener_detalle(input_data=body, auth_context=auth_context)
