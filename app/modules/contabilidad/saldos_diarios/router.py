from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.contabilidad.saldos_diarios.dependencies import get_saldos_diarios_service
from app.modules.contabilidad.saldos_diarios.schemas import ConsultaSaldosDiarios, SaldosDiariosResponse
from app.modules.contabilidad.saldos_diarios.service import SaldosDiariosService

router = APIRouter(tags=["Analytic Sac - Contabilidad"])


@router.post("/contabilidad/saldos-diarios", response_model=SaldosDiariosResponse,
             summary="Consultar todas las cuentas contables por día")
def consultar_saldos_diarios(
    body: ConsultaSaldosDiarios,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: SaldosDiariosService = Depends(get_saldos_diarios_service),
) -> SaldosDiariosResponse:
    return service.consultar(body)
