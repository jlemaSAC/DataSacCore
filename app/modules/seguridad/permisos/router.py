from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.seguridad.permisos.dependencies import get_permiso_service
from app.modules.seguridad.permisos.schemas import AccessBatchRequest, AccessBatchResponse, AccessStateResponse
from app.modules.seguridad.permisos.service import PermisoService

router = APIRouter(prefix="/permisos", tags=["Seguridad - Permisos"])


@router.get("", response_model=AccessStateResponse)
def consultar_permisos(
    context: AuthContext = Depends(get_current_auth_context),
    service: PermisoService = Depends(get_permiso_service),
) -> AccessStateResponse:
    return service.get_state(context)


@router.patch("", response_model=AccessBatchResponse)
def guardar_permisos(
    body: AccessBatchRequest,
    context: AuthContext = Depends(get_current_auth_context),
    service: PermisoService = Depends(get_permiso_service),
) -> AccessBatchResponse:
    return service.save(context, body)
