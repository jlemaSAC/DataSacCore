from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.depositos_a_plazos.resumen_depositos_a_plazo.dependencies import (
    get_resumen_depositos_a_plazo_service,
)
from app.modules.negocios.depositos_a_plazos.resumen_depositos_a_plazo.schemas import (
    ResumenDepositosAPlazoResponse,
)
from app.modules.negocios.depositos_a_plazos.resumen_depositos_a_plazo.service import (
    ResumenDepositosAPlazoService,
)
from app.modules.negocios.inversiones.depositos_a_plazo.schemas import InputResumenActualDepositos


router = APIRouter(prefix="/depositos-a-plazos", tags=["Negocios - Depósitos a Plazo"])


@router.post(
    "/resumen-depositos-a-plazo",
    response_model=ResumenDepositosAPlazoResponse,
    summary="Indicadores de DPF, detalle por dimensión y depósitos diarios por condición",
    description=(
        "Usa el mismo universo del resumen actual de inversiones: corte SQL y comparativos "
        "mensuales de Mongo/ETL. El rango debe pertenecer al mismo mes. Las tasas se "
        "ponderan por operaciones. El diario agrupa los DPF que permanecen al corte por "
        "fecha de creación y condición; no incluye cancelaciones anteriores al corte."
    ),
)
def obtener_resumen_depositos_a_plazo(
    body: InputResumenActualDepositos,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ResumenDepositosAPlazoService = Depends(get_resumen_depositos_a_plazo_service),
) -> ResumenDepositosAPlazoResponse:
    return service.obtener_resumen(body, auth)
