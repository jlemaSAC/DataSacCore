from fastapi import APIRouter, Depends

from app.modules.analytic.cartera_de_credito.morosidad_historica.dependencies import (
    get_morosidad_historica_cache_admin_service,
    get_morosidad_historica_service,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.schemas import (
    InputMorosidadHistorica,
    MorosidadHistoricaCacheClearResponse,
    MorosidadHistoricaResponse,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.service import (
    MorosidadHistoricaCacheAdminService,
    MorosidadHistoricaService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(tags=["Analytic Sac - Cartera de credito"])


@router.post(
    "/cartera-de-credito/morosidad-historica",
    response_model=MorosidadHistoricaResponse,
    summary="Consultar morosidad historica por meses",
    description="""
Consulta `SituacionCrediticia` en el ultimo dia calendario de los meses cerrados
y `SituacionCrediticiaActual` para el mes actual.
Devuelve saldo de capital y cartera improductiva por agrupacion para que el
frontend calcule la morosidad.
No se admiten meses posteriores al mes de la fecha del sistema.
""",
)
def obtener_morosidad_historica(
    body: InputMorosidadHistorica,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: MorosidadHistoricaService = Depends(get_morosidad_historica_service),
) -> MorosidadHistoricaResponse:
    return service.obtener_morosidad_historica(body, auth_context)


@router.delete(
    "/cartera-de-credito/morosidad-historica/cache",
    response_model=MorosidadHistoricaCacheClearResponse,
    summary="Limpiar cache Redis de morosidad historica",
    description="Elimina unicamente las claves Redis de morosidad historica. Requiere rol administrador.",
)
def limpiar_cache_morosidad_historica(
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: MorosidadHistoricaCacheAdminService = Depends(
        get_morosidad_historica_cache_admin_service
    ),
) -> MorosidadHistoricaCacheClearResponse:
    return service.limpiar_cache(auth_context)
