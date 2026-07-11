from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.nomina.cargos.dependencies import get_cargo_service
from app.modules.nomina.cargos.schemas import CargoResponse
from app.modules.nomina.cargos.service import CargoService


router = APIRouter(tags=["Nómina"])


@router.get(
    "/cargos",
    response_model=list[CargoResponse],
    summary="Listar cargos de nómina",
)
def listar_cargos(
    activo: bool | None = None,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: CargoService = Depends(get_cargo_service),
) -> list[CargoResponse]:
    return service.list_cargos(auth_context=auth_context, activo=activo)
