from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext

from .dependencies import get_control_cuentas_por_inactivarse_service
from .schemas import (
    ConsultaCuentasPorInactivarse,
    ConsultaCuentasPorInactivarseResponse,
    DetalleCuentasPorInactivarseRequest,
    DetalleCuentasPorInactivarseResponse,
)
from .service import ControlCuentasPorInactivarseService


router = APIRouter(prefix="/cuentas/control-de-cuentas-por-inactivarse", tags=["Negocios - Cuentas"])


@router.post("", response_model=ConsultaCuentasPorInactivarseResponse)
def consultar_cuentas_por_inactivarse(
    body: ConsultaCuentasPorInactivarse,
    auth: AuthContext = Depends(get_current_auth_context),
    servicio: ControlCuentasPorInactivarseService = Depends(get_control_cuentas_por_inactivarse_service),
) -> ConsultaCuentasPorInactivarseResponse:
    return servicio.consultar(body, auth)


@router.post("/detalle", response_model=DetalleCuentasPorInactivarseResponse)
def consultar_detalle_cuentas_por_inactivarse(
    body: DetalleCuentasPorInactivarseRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    servicio: ControlCuentasPorInactivarseService = Depends(get_control_cuentas_por_inactivarse_service),
) -> DetalleCuentasPorInactivarseResponse:
    return servicio.detalle(body, auth)
