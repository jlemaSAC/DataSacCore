from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.recuperacion.recaudacion_acumulada.dependencies import (
    get_asesores_agencia_service,
    get_recaudacion_acumulada_service,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.schemas import (
    AsesorAgenciaResponse,
    InputAsesoresPorAgencia,
    InputRecaudacionAcumulada,
    RecaudacionAcumuladaResponse,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.service import (
    AsesoresAgenciaService,
    RecaudacionAcumuladaService,
)


router = APIRouter(prefix="/recuperacion", tags=["Negocios - Recuperacion"])


@router.post(
    "/recaudacion-acumulada/asesores",
    response_model=list[AsesorAgenciaResponse],
    summary="Listar asesores de recuperación por agencia",
)
def listar_asesores_por_agencia(
    body: InputAsesoresPorAgencia,
    _auth_context: AuthContext = Depends(get_current_auth_context),
    service: AsesoresAgenciaService = Depends(get_asesores_agencia_service),
) -> list[AsesorAgenciaResponse]:
    return service.listar(body.ids_agencia)


@router.post(
    "/recaudacion-acumulada",
    response_model=RecaudacionAcumuladaResponse,
    summary="Obtener préstamos con recaudación acumulada",
)
def obtener_recaudacion_acumulada(
    body: InputRecaudacionAcumulada,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: RecaudacionAcumuladaService = Depends(
        get_recaudacion_acumulada_service
    ),
) -> RecaudacionAcumuladaResponse:
    return service.obtener_recaudacion_acumulada(body, auth_context)
