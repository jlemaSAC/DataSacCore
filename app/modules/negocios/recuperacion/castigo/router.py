from fastapi import APIRouter, Depends

from app.modules.negocios.recuperacion.castigo.dependencies import get_castigo_service
from app.modules.negocios.recuperacion.castigo.schemas import (
    DepositosCastigoResponse,
    InputDepositosCastigo,
    InputDetalleDepositosCastigo,
    DetalleDepositosCastigoResponse,
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
        "Fija los préstamos JUDICIAL o CASTIGADO y sus dimensiones en fecha_desde, "
        "sin excluir acumulados cero ni préstamos que se cancelen después. "
        "Calcula cada día por diferencia de DepositosMes de SituacionCrediticia, "
        "con base cero el primer día del mes y corte previo para rangos parciales. "
        "Completa el día actual mediante el mismo cálculo del reporte SQL. "
        "El seguimiento es por préstamo, incluso si un cliente tiene varios."
    ),
)
def obtener_depositos_diarios_castigo(
    body: InputDepositosCastigo,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: CastigoService = Depends(get_castigo_service),
) -> DepositosCastigoResponse:
    return service.obtener_depositos_diarios(body, auth_context)


@router.post(
    "/castigo/depositos-diarios/detalle",
    response_model=DetalleDepositosCastigoResponse,
    response_model_by_alias=True,
    summary="Consultar préstamos y movimientos en cuentas del importe seleccionado",
    description=(
        "Verifica los préstamos contra el universo inicial del rango. "
        "Devuelve las variaciones de DepositosMes por préstamo y los créditos en cuentas "
        "paginados, sin duplicar un movimiento cuando corresponde a varios préstamos."
    ),
)
def obtener_detalle_depositos_castigo(
    body: InputDetalleDepositosCastigo,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: CastigoService = Depends(get_castigo_service),
) -> DetalleDepositosCastigoResponse:
    return service.obtener_detalle_depositos(body, auth_context)
