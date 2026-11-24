from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext

from .dependencies import get_control_cuentas_inactivas_service
from .schemas import (
    ConsultaCuentasInactivas,
    ConsultaCuentasInactivasResponse,
    DetalleCuentasInactivasRequest,
    DetalleCuentasInactivasResponse,
)
from .service import ControlCuentasInactivasService


router = APIRouter(prefix="/cuentas/control-cuentas-inactivas", tags=["Negocios - Cuentas"])


@router.post("", response_model=ConsultaCuentasInactivasResponse)
def consultar_cuentas_inactivas(
    body: ConsultaCuentasInactivas,
    auth: AuthContext = Depends(get_current_auth_context),
    servicio: ControlCuentasInactivasService = Depends(get_control_cuentas_inactivas_service),
) -> ConsultaCuentasInactivasResponse:
    return servicio.consultar(body, auth)


@router.post("/detalle", response_model=DetalleCuentasInactivasResponse)
def consultar_detalle_cuentas_inactivas(
    body: DetalleCuentasInactivasRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    servicio: ControlCuentasInactivasService = Depends(get_control_cuentas_inactivas_service),
) -> DetalleCuentasInactivasResponse:
    return servicio.detalle(body, auth)
