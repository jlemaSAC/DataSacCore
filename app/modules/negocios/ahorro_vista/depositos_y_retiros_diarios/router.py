from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.ahorro_vista.depositos_y_retiros_diarios.dependencies import (
    get_depositos_y_retiros_diarios_service,
)
from app.modules.negocios.ahorro_vista.depositos_y_retiros_diarios.schemas import (
    DepositosYRetirosDiariosRequest,
    DepositosYRetirosDiariosResponse,
)
from app.modules.negocios.ahorro_vista.depositos_y_retiros_diarios.service import (
    DepositosYRetirosDiariosService,
)


router = APIRouter(prefix="/ahorro-vista", tags=["Negocios - Ahorro Vista"])


@router.post(
    "/depositos-y-retiros-diarios", response_model=DepositosYRetirosDiariosResponse,
    responses={503: {"description": "Conflicto temporal de bloqueos tras tres intentos; incluye Retry-After."}},
    summary="Depósitos y retiros diarios por asesor oficial, agencia y producto de Ahorro Vista",
    description=(
        "Rango de un mismo mes; id_agencia=0 consulta el consolidado. Incluye cualquier "
        "tipo de operación que cambie el saldo total de una cuenta de Ahorro Vista, "
        "incluyendo transferencias, intereses, cobros, aperturas y cierres. Calcula "
        "créditos menos débitos por operación y cuenta: una variación positiva suma "
        "depósitos y una negativa suma retiros por su magnitud. Excluye operaciones "
        "con variación cero, como traslados internos, y productos programados y aportaciones. "
        "Excluye la operación anulada si su reversión ocurrió hasta fecha_corte y siempre "
        "excluye el movimiento de reversión. Fecha por FECHASISTEMA. Asesor, agencia y "
        "producto de la cuenta al corte final; nombres del catálogo actual. Incluye "
        "movimientos de cuentas cerradas. Cada fila tiene los dos montos por día, "
        "completando ceros sin acumular. Permite Resumen por agencia y Detalle por asesor, "
        "con filtro de productos sobre la respuesta, sin consultas adicionales. Cada día "
        "incluye transacciones agrupadas por tipo y sentido, con valor positivo y "
        "es_debito=true para salidas o false para entradas; no son operaciones individuales."
    ),
)
def obtener_depositos_y_retiros_diarios(
    body: DepositosYRetirosDiariosRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: DepositosYRetirosDiariosService = Depends(get_depositos_y_retiros_diarios_service),
) -> DepositosYRetirosDiariosResponse:
    return service.obtener(body, auth)
