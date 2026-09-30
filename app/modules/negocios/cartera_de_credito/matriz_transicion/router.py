from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.matriz_transicion.dependencies import (
    get_matriz_transicion_service,
)
from app.modules.negocios.cartera_de_credito.matriz_transicion.schemas import (
    MatrizTransicionRequest,
    MatrizTransicionResponse,
)
from app.modules.negocios.cartera_de_credito.matriz_transicion.service import MatrizTransicionService


router = APIRouter(prefix="/cartera-de-credito", tags=["Negocios - Cartera de credito"])


@router.post(
    "/matriz-transicion/tiempo-real",
    response_model=MatrizTransicionResponse,
    summary="Matriz de transición entre dos cortes seleccionados",
)
def obtener_matriz_transicion_tiempo_real(
    request: MatrizTransicionRequest,
    _: AuthContext = Depends(get_current_auth_context),
    service: MatrizTransicionService = Depends(get_matriz_transicion_service),
) -> MatrizTransicionResponse:
    """Compara fecha_corte_anterior contra fecha_corte_nuevo."""
    return service.obtener(request)
