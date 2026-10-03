from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.recuperacion.evaluacion_recuperacion.dependencies import (
    get_detalle_evaluacion_recuperacion_service,
    get_evaluacion_recuperacion_service,
)
from app.modules.negocios.recuperacion.evaluacion_recuperacion.schemas import (
    DetalleEvaluacionRecuperacionResponse,
    InputDetalleEvaluacionRecuperacion,
    InputEvaluacionRecuperacion,
    EvaluacionRecuperacionResponse,
)
from app.modules.negocios.recuperacion.evaluacion_recuperacion.service import (
    EvaluacionRecuperacionService,
)


router = APIRouter(prefix="/recuperacion", tags=["Negocios - Recuperacion"])


@router.post(
    "/evaluacion-recuperacion",
    response_model=EvaluacionRecuperacionResponse,
    summary="Obtener evaluación comparativa de recuperación por agencia",
)
def obtener_evaluacion_recuperacion(
    body: InputEvaluacionRecuperacion,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: EvaluacionRecuperacionService = Depends(get_evaluacion_recuperacion_service),
) -> EvaluacionRecuperacionResponse:
    return service.obtener_evaluacion(input_data=body, auth_context=auth_context)


@router.post(
    "/evaluacion-recuperacion/detalle",
    response_model=DetalleEvaluacionRecuperacionResponse,
    summary="Obtener detalle paginado de evaluación de recuperación con estado operativo actual",
)
def obtener_detalle_evaluacion_recuperacion(
    body: InputDetalleEvaluacionRecuperacion,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: EvaluacionRecuperacionService = Depends(
        get_detalle_evaluacion_recuperacion_service
    ),
) -> DetalleEvaluacionRecuperacionResponse:
    return service.obtener_detalle(input_data=body, auth_context=auth_context)
