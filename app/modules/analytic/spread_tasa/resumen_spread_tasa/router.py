from fastapi import APIRouter, Depends

from app.modules.analytic.spread_tasa.resumen_spread_tasa.dependencies import get_resumen_spread_tasa_service
from app.modules.analytic.spread_tasa.resumen_spread_tasa.schemas import ResumenSpreadTasaInput, ResumenSpreadTasaResponse, SpreadAgenciasInput, SpreadAgenciasResponse
from app.modules.analytic.spread_tasa.resumen_spread_tasa.service import ResumenSpreadTasaService
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext

router = APIRouter(prefix="/spread-tasa", tags=["Analytic Sac - Spread de Tasa"])


@router.post("/resumen-spread-tasa", response_model=ResumenSpreadTasaResponse, summary="Consultar resumen de spread de tasa por agencia")
def resumen_spread_tasa(
    body: ResumenSpreadTasaInput,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ResumenSpreadTasaService = Depends(get_resumen_spread_tasa_service),
) -> ResumenSpreadTasaResponse:
    return service.consultar(body.fecha_corte, body.id_agencia)


@router.post('/spread-por-agencia', response_model=SpreadAgenciasResponse, summary='Consultar spread por agencia')
def spread_por_agencia(
    body: SpreadAgenciasInput,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ResumenSpreadTasaService = Depends(get_resumen_spread_tasa_service),
) -> SpreadAgenciasResponse:
    return service.consultar_agencias(body.fecha_corte, body.ids_agencia)
