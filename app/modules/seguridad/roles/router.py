from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.seguridad.roles.dependencies import get_rol_service
from app.modules.seguridad.roles.schemas import RolResponse
from app.modules.seguridad.roles.service import RolService


router = APIRouter(tags=["Seguridad"])


@router.get(
    "/roles",
    response_model=list[RolResponse],
    summary="Listar roles de seguridad",
)
def listar_roles(
    activo: bool | None = None,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: RolService = Depends(get_rol_service),
) -> list[RolResponse]:
    return service.list_roles(auth_context=auth_context, activo=activo)
