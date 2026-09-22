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


router = APIRouter(tags=["Analytic Sac - Cartera de credito"])


@router.post(
    "/cartera-de-credito/comparativo",
    response_model=ComparativoCarteraResponse,
    summary="Comparar diariamente las metricas de cartera",
description="""
Devuelve un punto por cada fecha del rango y usa como referencias el cierre del
mes anterior y el cierre del año anterior. El rango debe pertenecer a un solo mes.
Una lista de agencias vacia representa el consolidado institucional.
""",
)
def obtener_comparativo_cartera(
    body: InputComparativoCartera,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ComparativoCarteraService = Depends(get_comparativo_cartera_service),
) -> ComparativoCarteraResponse:
    return service.obtener_comparativo(body, auth_context)
