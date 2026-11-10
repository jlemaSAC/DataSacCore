from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.ahorro_restringido.control_vencimiento_restringido.dependencies import get_control_vencimiento_restringido_service
from app.modules.negocios.ahorro_restringido.control_vencimiento_restringido.schemas import (
    ControlVencimientoRestringidoRequest,
    ControlVencimientoRestringidoResponse,
    DetalleControlVencimientoRestringidoRequest,
    DetalleControlVencimientoRestringidoResponse,
)
from app.modules.negocios.ahorro_restringido.control_vencimiento_restringido.service import ControlVencimientoRestringidoService


router = APIRouter(prefix="/ahorro-restringido", tags=["Negocios - Ahorro Restringido"])


@router.post(
    "/control-vencimiento-restringido", response_model=ControlVencimientoRestringidoResponse,
    summary="Saldo actual por vencimiento de ahorro restringido, agencia, asesor y producto",
    description=(
        "Cuentas programadas en estados A/I/B con contrato activo cuya FECHAVENCIMIENTO "
        "está entre fecha_inicio y fecha_fin, incluyendo ambos días. Permite fechas futuras y "
        "rangos de varios meses. El saldo, los cargos y responsables son actuales; no es un corte histórico."
    ),
)
def obtener_control_vencimiento(
    body: ControlVencimientoRestringidoRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ControlVencimientoRestringidoService = Depends(get_control_vencimiento_restringido_service),
) -> ControlVencimientoRestringidoResponse:
    return service.obtener(body, auth)


@router.post(
    "/control-vencimiento-restringido/detalle", response_model=DetalleControlVencimientoRestringidoResponse,
    summary="Detalle de cuentas de ahorro restringido por vencimiento",
    description=(
        "Conserva el universo y los filtros del resumen. Incluye producto, cuenta, saldo actual, "
        "tasa del contrato activo, vencimiento, estado y cliente principal. "
        "Tiene préstamo indica un préstamo no cancelado del cliente principal con vínculo activo. "
        "Puede devolver una página o todos los registros si sin_paginacion es true."
    ),
)
def obtener_detalle_control_vencimiento(
    body: DetalleControlVencimientoRestringidoRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ControlVencimientoRestringidoService = Depends(get_control_vencimiento_restringido_service),
) -> DetalleControlVencimientoRestringidoResponse:
    return service.obtener_detalle(body)
