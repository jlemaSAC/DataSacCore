from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.dependencies import (
    get_situacion_crediticia_asesores_service,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.schemas import (
    SituacionCrediticiaAsesoresRequest,
    SituacionCrediticiaAsesoresResponse,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.service import (
    SituacionCrediticiaAsesoresService,
)


router = APIRouter(
    prefix="/cartera-de-credito",
    tags=["Negocios - Cartera de credito"],
)


@router.post(
    "/situacion-crediticia/asesores-comparacion",
    response_model=SituacionCrediticiaAsesoresResponse,
    summary="Comparar situación crediticia de asesores por rango mensual",
    description=(
        "Usa fecha_inicio y fecha_fin para determinar el mes y compara fecha_fin "
        "contra el cierre del mes anterior. "
        "id_agencia=0 devuelve el consolidado de todas las agencias."
    ),
)
def obtener_situacion_crediticia_asesores(
    request: SituacionCrediticiaAsesoresRequest,
    _: AuthContext = Depends(get_current_auth_context),
    service: SituacionCrediticiaAsesoresService = Depends(
        get_situacion_crediticia_asesores_service
    ),
) -> SituacionCrediticiaAsesoresResponse:
    return service.obtener(
        fecha_inicio=request.fecha_inicio,
        fecha_fin=request.fecha_fin,
        id_agencia=request.id_agencia,
        filtrar_diferidos=request.filtrar_diferidos,
    )
