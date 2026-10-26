from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.dependencies import (
    get_control_diario_captaciones_service,
)
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.schemas import (
    ControlDiarioCaptacionesRequest,
    ControlDiarioCaptacionesResponse,
    DetalleControlCaptacionesRequest,
    DetalleControlCaptacionesResponse,
)
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.service import ControlDiarioCaptacionesService


router = APIRouter(prefix="/depositos-a-plazos", tags=["Negocios - Depósitos a Plazo"])


@router.post(
    "/control-diario-captaciones",
    response_model=ControlDiarioCaptacionesResponse,
    summary="Montos diarios por captador, agencia y condición",
    description=(
        "Rango de un mismo mes. Incluye los depósitos creados en el rango sin filtrar por "
        "estado al corte, incluso cancelados y anulados. Agrupa por fecha de creación. "
        "Devuelve montos nuevos y renovados "
        "por separado, con cero en días sin captaciones. Cargo corresponde al catálogo actual."
    ),
)
def obtener_control_diario_captaciones(
    body: ControlDiarioCaptacionesRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ControlDiarioCaptacionesService = Depends(get_control_diario_captaciones_service),
) -> ControlDiarioCaptacionesResponse:
    return service.obtener(body, auth)


@router.post(
    "/control-diario-captaciones/detalle",
    response_model=DetalleControlCaptacionesResponse,
    summary="Detalle completo de los DPF de un monto diario o del período, sin paginación",
    description=(
        "Mantiene fecha_fin como corte original del control diario. fecha limita el día de creación, "
        "sin mover el corte. Aplica agencia, captador, cargos y condición sobre el mismo universo. "
        "Incluye todos los depósitos creados en el rango, independientemente de su estado, "
        "con monto, interés total y tasa total al corte, sin paginación."
    ),
)
def obtener_detalle_control_diario_captaciones(
    body: DetalleControlCaptacionesRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ControlDiarioCaptacionesService = Depends(get_control_diario_captaciones_service),
) -> DetalleControlCaptacionesResponse:
    return service.obtener_detalle(body, auth)
