from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.depositos_a_plazos.control_vencimiento.dependencies import get_control_vencimiento_service
from app.modules.negocios.depositos_a_plazos.control_vencimiento.schemas import (
    ControlVencimientoRequest,
    ControlVencimientoResponse,
    DetalleControlVencimientoRequest,
    DetalleControlVencimientoResponse,
)
from app.modules.negocios.depositos_a_plazos.control_vencimiento.service import ControlVencimientoService


router = APIRouter(prefix="/depositos-a-plazos", tags=["Negocios - Depósitos a plazos"])


@router.post(
    "/control-vencimiento", response_model=ControlVencimientoResponse,
    summary="Saldo de DPF por vencer agrupado por agencia y captador",
    description=(
        "Consulta el capital actual de los DPF activos, exigibles y vencidos cuya FECHAVENCIMIENTO "
        "está entre fecha_inicio y fecha_fin, incluyendo ambos días. Permite fechas futuras y "
        "rangos de varios meses. Los cargos y responsables corresponden a los datos actuales."
    ),
)
def obtener_control_vencimiento(
    body: ControlVencimientoRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ControlVencimientoService = Depends(get_control_vencimiento_service),
) -> ControlVencimientoResponse:
    return service.obtener(body, auth)


@router.post(
    "/control-vencimiento/detalle", response_model=DetalleControlVencimientoResponse,
    summary="Detalle paginado de DPF por vencer para una agencia o captador",
    description=(
        "Conserva el universo A/E/V y los filtros del resumen. Interés total es la suma de "
        "CALCULADO de los ítems de interés, incluyendo los pagados. La tasa total es la tasa "
        "efectiva. Tiene préstamo corresponde al cliente principal con un préstamo no cancelado."
    ),
)
def obtener_detalle_control_vencimiento(
    body: DetalleControlVencimientoRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ControlVencimientoService = Depends(get_control_vencimiento_service),
) -> DetalleControlVencimientoResponse:
    return service.obtener_detalle(body)
