from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.analytic.analisis_contable.cuentas_contables.dependencies import get_cuentas_contables_service
from app.modules.analytic.analisis_contable.cuentas_contables.schemas import ConsultaCuentasContables, ResumenCuentasContables
from app.modules.analytic.analisis_contable.cuentas_contables.service import CuentasContablesService

router = APIRouter(tags=["Analytic Sac - Análisis Contable"])


@router.post("/cuentas-contables", response_model=ResumenCuentasContables,
             summary="Consultar diez indicadores contables a una fecha de corte")
def consultar_cuentas_contables(
    body: ConsultaCuentasContables,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: CuentasContablesService = Depends(get_cuentas_contables_service),
) -> ResumenCuentasContables:
    return service.consultar(body)
