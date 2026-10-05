from fastapi import APIRouter, Depends, Query

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.inicio.dependencies import get_negocio_inicio_service
from app.modules.negocios.inicio.schemas import NegocioInicioResponse
from app.modules.negocios.inicio.service import NegocioInicioService


router = APIRouter(tags=["Negocios - Inicio"])


@router.get(
    "/inicio",
    response_model=NegocioInicioResponse,
    summary="Obtener colocación y cartera del día para una agencia",
)
def obtener_inicio_negocio(
    id_agencia: int = Query(gt=0),
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: NegocioInicioService = Depends(get_negocio_inicio_service),
) -> NegocioInicioResponse:
    return service.obtener(id_agencia=id_agencia, auth_context=auth_context)
