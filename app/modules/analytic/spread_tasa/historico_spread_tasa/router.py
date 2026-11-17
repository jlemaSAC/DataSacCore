from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from .dependencies import get_historico_spread_tasa_service
from .schemas import HistoricoSpreadTasaInput, HistoricoSpreadTasaResponse
from .service import HistoricoSpreadTasaService

router = APIRouter(prefix='/spread-tasa', tags=['Analytic Sac - Spread de Tasa'])


@router.post('/historico-spread-de-tasa', response_model=HistoricoSpreadTasaResponse)
def historico_spread_de_tasa(
    body: HistoricoSpreadTasaInput,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: HistoricoSpreadTasaService = Depends(get_historico_spread_tasa_service),
) -> HistoricoSpreadTasaResponse:
    return service.consultar(body)
