from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.ahorro_restringido.control_diario_cancelacion.dependencies import (
    get_cancelacion_restringidos_service,
)
from app.modules.negocios.ahorro_restringido.control_diario_cancelacion.schemas import (
    ControlCancelacionRestringidosRequest,
    ControlCancelacionRestringidosResponse,
    DetalleCancelacionRestringidosRequest,
    DetalleCancelacionRestringidosResponse,
)
from app.modules.negocios.ahorro_restringido.control_diario_cancelacion.service import (
    ControlCancelacionRestringidosService,
)

router = APIRouter(prefix="/ahorro-restringido", tags=["Negocios - Ahorro Restringido"])


@router.post(
    "/control-diario-cancelacion-restringidos",
    response_model=ControlCancelacionRestringidosResponse,
    description=(
        "Último cierre válido (transacción 30) de cuentas programadas cerradas al corte. "
        "Monto debitado en ítems SUMASALDO=1, sin duplicar intereses internos ni incluir reversos."
    ),
)
def obtener_control(
    body: ControlCancelacionRestringidosRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ControlCancelacionRestringidosService = Depends(get_cancelacion_restringidos_service),
) -> ControlCancelacionRestringidosResponse:
    return service.obtener(body, auth)


@router.post(
    "/control-diario-cancelacion-restringidos/detalle",
    response_model=DetalleCancelacionRestringidosResponse,
)
def obtener_detalle(
    body: DetalleCancelacionRestringidosRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ControlCancelacionRestringidosService = Depends(get_cancelacion_restringidos_service),
) -> DetalleCancelacionRestringidosResponse:
    return service.obtener_detalle(body, auth)
