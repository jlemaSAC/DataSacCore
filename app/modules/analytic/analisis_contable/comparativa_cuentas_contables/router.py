from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.dependencies import get_comparativa_cuentas_service
from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.schemas import ComparativaCuentasResponse, ConsultaComparativaCuentas
from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.service import ComparativaCuentasService

router = APIRouter(tags=["Analytic Sac - Análisis Contable"])


@router.post("/comparativa-cuentas-contables", response_model=ComparativaCuentasResponse,
             summary="Comparar todas las cuentas al mismo día de cada mes")
def consultar_comparativa_cuentas(
    body: ConsultaComparativaCuentas,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ComparativaCuentasService = Depends(get_comparativa_cuentas_service),
) -> ComparativaCuentasResponse:
    return service.consultar(body)
