from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.dependencies import (
    get_control_diario_captaciones_service,
)
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.schemas import (
    ControlDiarioCaptacionesRequest,
    ControlDiarioCaptacionesResponse,
)
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.service import ControlDiarioCaptacionesService


router = APIRouter(prefix="/depositos-a-plazos", tags=["Negocios - Depósitos a Plazo"])


@router.post(
    "/control-diario-captaciones",
    response_model=ControlDiarioCaptacionesResponse,
    summary="Montos diarios por captador, agencia y condición",
    description=(
        "Rango de un mismo mes. Usa el universo del resumen de depósitos al corte: "
        "DPF activos, exigibles o vencidos con cliente principal, agrupados por fecha de creación. "
        "No incluye cancelaciones anteriores al corte. Devuelve montos nuevos y renovados "
        "por separado, con cero en días sin captaciones. Cargo corresponde al catálogo actual."
    ),
)
def obtener_control_diario_captaciones(
    body: ControlDiarioCaptacionesRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ControlDiarioCaptacionesService = Depends(get_control_diario_captaciones_service),
) -> ControlDiarioCaptacionesResponse:
    return service.obtener(body, auth)
