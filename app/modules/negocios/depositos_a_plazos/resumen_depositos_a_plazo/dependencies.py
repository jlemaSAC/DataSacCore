from fastapi import Depends

from app.modules.negocios.depositos_a_plazos.resumen_depositos_a_plazo.service import (
    ResumenDepositosAPlazoService,
)
from app.modules.negocios.inversiones.depositos_a_plazo.dependencies import (
    get_resumen_actual_depositos_service,
)
from app.modules.negocios.inversiones.depositos_a_plazo.service import ResumenActualDepositosService


def get_resumen_depositos_a_plazo_service(
    resumen: ResumenActualDepositosService = Depends(get_resumen_actual_depositos_service),
) -> ResumenDepositosAPlazoService:
    return ResumenDepositosAPlazoService(resumen)
