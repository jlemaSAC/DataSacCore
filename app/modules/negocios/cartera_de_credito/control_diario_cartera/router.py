from datetime import datetime

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext

from .dependencies import get_control_diario_cartera_service
from .schemas import ControlDiarioCarteraRequest, ControlDiarioCarteraResponse
from .service import ControlDiarioCarteraService

router = APIRouter(prefix="/cartera-de-credito/control-diario-cartera", tags=["Negocios - Cartera de credito"])


@router.post("/mensual", response_model=ControlDiarioCarteraResponse,
             summary="Variaciones por rango de fechas, asesor y agencia desde MongoDB")
def obtener_control_diario_cartera(
    request: ControlDiarioCarteraRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ControlDiarioCarteraService = Depends(get_control_diario_cartera_service),
) -> ControlDiarioCarteraResponse:
    fecha = auth.usuario.fecha_sistema
    return service.obtener(request, fecha_limite=fecha.date() if isinstance(fecha, datetime) else fecha)
