from fastapi import APIRouter, Depends

from app.modules.negocios.recuperacion.castigo.dependencies import get_castigo_service
from app.modules.negocios.recuperacion.castigo.schemas import (
    DepositosCastigoResponse,
    InputDepositosCastigo,
)
from app.modules.negocios.recuperacion.castigo.service import CastigoService
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(prefix="/recuperacion", tags=["Negocios - Recuperacion"])


@router.post(
    "/castigo/depositos-diarios",
    response_model=DepositosCastigoResponse,
    response_model_by_alias=True,
    summary="Consultar depósitos diarios de préstamos judiciales y castigados al inicio del rango",
    description=(
        "Solo incluye préstamos cuyo estado en fecha_desde era JUDICIAL o CASTIGADO. "
        "Devuelve sumas diarias y catálogos para filtrar por agencia, asesor y cargo."
    ),
)
def obtener_depositos_diarios_castigo(
    body: InputDepositosCastigo,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: CastigoService = Depends(get_castigo_service),
) -> DepositosCastigoResponse:
    return service.obtener_depositos_diarios(body, auth_context)
