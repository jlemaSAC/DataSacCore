from fastapi import APIRouter, Depends

from app.modules.analytic.cartera_de_credito.morosidad_historica.dependencies import (
    get_morosidad_historica_service,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.schemas import (
    InputMorosidadHistorica,
    MorosidadHistoricaResponse,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.service import (
    MorosidadHistoricaService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(tags=["Analytic Sac - Cartera de credito"])


@router.post(
    "/cartera-de-credito/morosidad-historica",
    response_model=MorosidadHistoricaResponse,
    summary="Consultar morosidad historica por meses cerrados",
    description="""
Consulta `SituacionCrediticia` en el ultimo dia calendario de cada mes.
La morosidad se calcula como `(CapitalNoDevenga + CapitalVencido) / SaldoCapital`.
Solo se admiten meses que hayan finalizado a la fecha del sistema.
""",
)
def obtener_morosidad_historica(
    body: InputMorosidadHistorica,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: MorosidadHistoricaService = Depends(get_morosidad_historica_service),
) -> MorosidadHistoricaResponse:
    return service.obtener_morosidad_historica(body, auth_context)

