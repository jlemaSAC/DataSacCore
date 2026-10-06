from fastapi import APIRouter, Depends, Query

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.colocacion.diaria_asesores.dependencies import (
    get_colocacion_diaria_asesores_service,
)
from app.modules.negocios.colocacion.diaria_asesores.schemas import (
    ColocacionDiariaAsesoresResponse,
)
from app.modules.negocios.colocacion.diaria_asesores.service import (
    ColocacionDiariaAsesoresService,
)


router = APIRouter(prefix="/colocacion", tags=["Negocios - Colocacion"])


@router.get(
    "/diaria-asesores",
    response_model=ColocacionDiariaAsesoresResponse,
    summary="Listar colocaciones del día por asesor de agencia",
)
def obtener_colocaciones_diarias_por_asesor(
    id_agencia: int = Query(gt=0),
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ColocacionDiariaAsesoresService = Depends(
        get_colocacion_diaria_asesores_service
    ),
) -> ColocacionDiariaAsesoresResponse:
    return service.obtener(id_agencia=id_agencia, auth_context=auth_context)
