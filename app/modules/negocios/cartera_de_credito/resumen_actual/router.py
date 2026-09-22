from fastapi import APIRouter, Depends

from app.modules.analytic.cartera_de_credito.comparativo_cartera.dependencies import (
    get_comparativo_cartera_service,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.schemas import (
    ComparativoCarteraResponse,
    InputComparativoCartera,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.service import (
    ComparativoCarteraService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(prefix="/cartera-de-credito", tags=["Negocios - Cartera de credito"])


@router.post(
    "/resumen-actual",
    response_model=ComparativoCarteraResponse,
    summary="Obtener resumen actual comparativo de cartera de credito",
    description=(
        "Devuelve los cortes diarios del rango y los cierres del mes y año anteriores. "
        "Una lista de agencias vacía representa el consolidado institucional."
    ),
)
def obtener_resumen_actual_cartera(
    body: InputComparativoCartera,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ComparativoCarteraService = Depends(get_comparativo_cartera_service),
) -> ComparativoCarteraResponse:
    return service.obtener_comparativo(body, auth_context)
