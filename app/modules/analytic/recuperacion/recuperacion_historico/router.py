from fastapi import APIRouter, Depends

from app.modules.analytic.recuperacion.recuperacion_historico.dependencies import (
    get_recuperacion_historico_service,
)
from app.modules.analytic.recuperacion.recuperacion_historico.schemas import (
    InputRecuperacionHistoricoAgrupado,
    InputRecuperacionHistoricoRango,
    RecuperacionHistoricoAgrupadoResponse,
    RecuperacionHistoricoCompactoResponse,
    RecuperacionHistoricoRangoResponse,
)
from app.modules.analytic.recuperacion.recuperacion_historico.service import RecuperacionHistoricoService
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(tags=["Analytic Sac - Recuperacion"])


@router.post(
    "/recuperacion/recuperacion-historico",
    response_model=RecuperacionHistoricoRangoResponse,
    response_model_by_alias=True,
    response_model_exclude_none=True,
    summary="Consultar recuperación histórica desde MongoDB",
)
def obtener_recuperacion_historica_por_rango(
    body: InputRecuperacionHistoricoRango,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: RecuperacionHistoricoService = Depends(get_recuperacion_historico_service),
) -> RecuperacionHistoricoRangoResponse:
    return service.obtener_recuperacion_por_rango(body, auth_context)


@router.post(
    "/recuperacion/recuperacion-historico-compacto",
    response_model=RecuperacionHistoricoCompactoResponse,
    summary="Consultar recuperación histórica compacta desde MongoDB",
)
def obtener_recuperacion_historica_compacta(
    body: InputRecuperacionHistoricoRango,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: RecuperacionHistoricoService = Depends(get_recuperacion_historico_service),
) -> RecuperacionHistoricoCompactoResponse:
    return service.obtener_recuperacion_compacta(body, auth_context)


@router.post(
    "/recuperacion/recuperacion-historico-agrupado",
    response_model=RecuperacionHistoricoAgrupadoResponse,
    summary="Consultar recuperación histórica agregada en MongoDB",
)
def obtener_recuperacion_historica_agrupada(
    body: InputRecuperacionHistoricoAgrupado,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: RecuperacionHistoricoService = Depends(get_recuperacion_historico_service),
) -> RecuperacionHistoricoAgrupadoResponse:
    return service.obtener_recuperacion_agrupada(body, auth_context)
