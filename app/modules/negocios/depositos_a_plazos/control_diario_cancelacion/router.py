from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.depositos_a_plazos.control_diario_cancelacion.dependencies import (
    get_control_diario_cancelacion_service,
)
from app.modules.negocios.depositos_a_plazos.control_diario_cancelacion.schemas import (
    ControlDiarioCancelacionRequest,
    ControlDiarioCancelacionResponse,
    DetalleControlCancelacionRequest,
    DetalleControlCancelacionResponse,
)
from app.modules.negocios.depositos_a_plazos.control_diario_cancelacion.service import ControlDiarioCancelacionService


router = APIRouter(prefix="/depositos-a-plazos", tags=["Negocios - Depósitos a Plazo"])


@router.post(
    "/control-diario-cancelacion",
    response_model=ControlDiarioCancelacionResponse,
    summary="Cancelaciones diarias por captador y agencia",
    description=(
        "Incluye únicamente depósitos en estado Cancelado al corte, agrupados por la fecha "
        "de su último movimiento válido de cancelación dentro del rango. Excluye reversos."
    ),
)
def obtener_control_diario_cancelacion(
    body: ControlDiarioCancelacionRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ControlDiarioCancelacionService = Depends(get_control_diario_cancelacion_service),
) -> ControlDiarioCancelacionResponse:
    return service.obtener(body, auth)


@router.post(
    "/control-diario-cancelacion/detalle",
    response_model=DetalleControlCancelacionResponse,
    summary="Detalle completo de los DPF de un monto diario o del período, sin paginación",
    description=(
        "Conserva fecha_fin como corte del control diario. fecha limita el día de cancelación; "
        "null consulta el rango completo. Aplica agencia, captador, cargos y condición "
        "sobre el mismo universo del resumen. Devuelve los depósitos sin paginación."
    ),
)
def obtener_detalle_control_diario_cancelacion(
    body: DetalleControlCancelacionRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ControlDiarioCancelacionService = Depends(get_control_diario_cancelacion_service),
) -> DetalleControlCancelacionResponse:
    return service.obtener_detalle(body, auth)
