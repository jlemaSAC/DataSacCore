from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.inversiones.depositos_a_plazo.dependencies import (
    get_resumen_actual_depositos_service,
)
from app.modules.negocios.inversiones.depositos_a_plazo.schemas import (
    InputResumenActualDepositos,
    ResumenActualDepositosResponse,
)
from app.modules.negocios.inversiones.depositos_a_plazo.service import ResumenActualDepositosService


router = APIRouter(prefix="/inversiones/depositos-a-plazo", tags=["Negocios - Inversiones"])


@router.post(
    "/resumen-actual",
    response_model=ResumenActualDepositosResponse,
    summary="Resumen de DPF al corte con cierres del mes y año anteriores",
    description=(
        "Tasas ponderadas por número de operaciones. La tasa promedio de renovación "
        "incluye todos los DPF creados entre fecha_inicio y fecha_fin, al corte disponible. "
        "fecha_fin determina el corte y el rango debe pertenecer al mismo mes. "
        "El corte real puede ser el último día operativo anterior a fecha_fin. "
        "El detalle por agencia contiene únicamente los indicadores actuales."
    ),
)
def obtener_resumen_actual_depositos(
    body: InputResumenActualDepositos,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ResumenActualDepositosService = Depends(get_resumen_actual_depositos_service),
) -> ResumenActualDepositosResponse:
    return service.obtener_resumen(body, auth)
