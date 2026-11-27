from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext

from .dependencies import get_control_cuentas_activas_service
from .schemas import (
    ConsultaCuentasReactivadas,
    ConsultaCuentasReactivadasResponse,
    DetalleCuentasReactivadasRequest,
    DetalleCuentasReactivadasResponse,
)
from .service import ControlCuentasActivasService


router = APIRouter(prefix="/cuentas/control-de-cuentas-activas", tags=["Negocios - Cuentas"])


@router.post("", response_model=ConsultaCuentasReactivadasResponse)
def consultar_cuentas_reactivadas(
    body: ConsultaCuentasReactivadas,
    auth: AuthContext = Depends(get_current_auth_context),
    servicio: ControlCuentasActivasService = Depends(get_control_cuentas_activas_service),
) -> ConsultaCuentasReactivadasResponse:
    return servicio.consultar(body, auth)


@router.post("/detalle", response_model=DetalleCuentasReactivadasResponse)
def consultar_detalle_cuentas_reactivadas(
    body: DetalleCuentasReactivadasRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    servicio: ControlCuentasActivasService = Depends(get_control_cuentas_activas_service),
) -> DetalleCuentasReactivadasResponse:
    return servicio.detalle(body, auth)
