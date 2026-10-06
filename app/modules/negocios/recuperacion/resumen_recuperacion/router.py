from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.recuperacion.resumen_recuperacion.dependencies import (
    get_resumen_recuperacion_service,
)
from app.modules.negocios.recuperacion.resumen_recuperacion.schemas import (
    InputResumenRecuperacion,
    ResumenActualRecuperacionResponse,
    ResumenRecuperacionResponse,
)
from app.modules.negocios.recuperacion.resumen_recuperacion.service import (
    ResumenRecuperacionService,
)

router = APIRouter(prefix="/recuperacion", tags=["Negocios - Recuperacion"])


@router.post(
    "/resumen",
    response_model=ResumenRecuperacionResponse,
    summary="Comparar recuperación con mes y año anteriores completos y consultar el diario",
)
def obtener_resumen_recuperacion(
    body: InputResumenRecuperacion,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ResumenRecuperacionService = Depends(get_resumen_recuperacion_service),
) -> ResumenRecuperacionResponse:
    return service.obtener_resumen(body, auth_context)


@router.post(
    "/resumen-actual",
    response_model=ResumenActualRecuperacionResponse,
    summary="Comparar recuperación con el mes y año anteriores completos",
)
def obtener_resumen_actual_recuperacion(
    body: InputResumenRecuperacion,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ResumenRecuperacionService = Depends(get_resumen_recuperacion_service),
) -> ResumenActualRecuperacionResponse:
    return service.obtener_resumen(body, auth_context)
