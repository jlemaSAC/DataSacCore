from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from .dependencies import get_costo_fondeo_service
from .schemas import CostoFondeoInput, CostoFondeoResponse
from .service import CostoFondeoService

router = APIRouter(prefix='/spread-tasa', tags=['Analytic Sac - Spread de Tasa'])


@router.post('/costo-de-fondeo', response_model=CostoFondeoResponse)
def costo_de_fondeo(
    body: CostoFondeoInput,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: CostoFondeoService = Depends(get_costo_fondeo_service),
) -> CostoFondeoResponse:
    return service.consultar(body)
