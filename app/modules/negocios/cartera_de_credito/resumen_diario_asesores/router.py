from fastapi import APIRouter, Depends, Query

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.dependencies import (
    get_resumen_diario_cartera_service,
)
from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.schemas import (
    ResumenDiarioCarteraAsesoresResponse,
)
from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.service import (
    ResumenDiarioCarteraService,
)


router = APIRouter(prefix="/cartera-de-credito", tags=["Negocios - Cartera de credito"])


@router.get(
    "/resumen-diario-asesores",
    response_model=ResumenDiarioCarteraAsesoresResponse,
    summary="Obtener saldo, provisiones y morosidad actual por asesor de agencia",
)
def obtener_resumen_diario_cartera_asesores(
    id_agencia: int = Query(gt=0),
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ResumenDiarioCarteraService = Depends(get_resumen_diario_cartera_service),
) -> ResumenDiarioCarteraAsesoresResponse:
    return service.obtener(id_agencia=id_agencia, auth_context=auth_context)
