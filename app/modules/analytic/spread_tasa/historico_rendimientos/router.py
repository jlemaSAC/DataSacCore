from fastapi import APIRouter, Depends
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from .dependencies import get_historico_rendimientos_service
from .schemas import HistoricoRendimientosInput, HistoricoRendimientosResponse
from .service import HistoricoRendimientosService

router = APIRouter(prefix='/spread-tasa', tags=['Analytic Sac - Spread de Tasa'])


@router.post('/historico-rendimientos', response_model=HistoricoRendimientosResponse)
def historico_rendimientos(
    body: HistoricoRendimientosInput,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: HistoricoRendimientosService = Depends(get_historico_rendimientos_service),
) -> HistoricoRendimientosResponse:
    return service.consultar(body)
