from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.colocacion.resumen.dependencies import get_resumen_colocacion_service
from app.modules.negocios.colocacion.resumen.schemas import (
    DetalleResumenColocacionResponse,
    InputDetalleResumenColocacion,
    InputResumenActualColocacion,
    InputResumenColocacion,
    ResumenActualColocacionConAdjudicadosResponse,
    ResumenActualColocacionResponse,
    ResumenColocacionResponse,
)
from app.modules.negocios.colocacion.resumen.service import ResumenColocacionService


router = APIRouter(prefix="/colocacion", tags=["Negocios - Colocacion"])


@router.post(
    "/evaluacion-colocacion",
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
    "/resumen-actual",
    response_model=ResumenActualColocacionResponse,
    summary="Comparar el resumen de colocación para un rango",
)
def obtener_resumen_actual_colocacion(
    body: InputResumenActualColocacion,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ResumenColocacionService = Depends(get_resumen_colocacion_service),
) -> ResumenActualColocacionResponse:
    return service.obtener_resumen_actual(input_data=body, auth_context=auth_context)


@router.post(
    "/resumen-actual-adjudicados",
    response_model=ResumenActualColocacionConAdjudicadosResponse,
    summary="Comparar colocación y listar préstamos adjudicados por agencia",
)
def obtener_resumen_actual_colocacion_con_adjudicados(
    body: InputResumenActualColocacion,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ResumenColocacionService = Depends(get_resumen_colocacion_service),
) -> ResumenActualColocacionConAdjudicadosResponse:
    return service.obtener_resumen_actual_con_adjudicados(
        input_data=body,
        auth_context=auth_context,
    )


@router.post(
    "/evaluacion-colocacion/detalle",
    response_model=DetalleResumenColocacionResponse,
    summary="Obtener operaciones de una fila del resumen de colocación",
)
def obtener_detalle_resumen_colocacion(
    body: InputDetalleResumenColocacion,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ResumenColocacionService = Depends(get_resumen_colocacion_service),
) -> DetalleResumenColocacionResponse:
    return service.obtener_detalle(input_data=body, auth_context=auth_context)
