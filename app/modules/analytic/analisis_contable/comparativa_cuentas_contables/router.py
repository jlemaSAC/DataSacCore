from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.dependencies import get_comparativa_cuentas_service
from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.schemas import (
    ComparativaCuentasResponse, ConsultaComparativaCuentas,
    ComparativaAnualMesesResponse, ConsultaComparativaAnualMeses,
)
from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.service import ComparativaCuentasService

router = APIRouter(tags=["Analytic Sac - Análisis Contable"])


@router.post("/comparativa-cuentas-contables", response_model=ComparativaCuentasResponse,
             summary="Comparar cuentas por día, o al mismo día de cada mes o año")
def consultar_comparativa_cuentas(
    body: ConsultaComparativaCuentas,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ComparativaCuentasService = Depends(get_comparativa_cuentas_service),
) -> ComparativaCuentasResponse:
    return service.consultar(body)


@router.post("/comparativa-cuentas-contables/anual-por-meses", response_model=ComparativaAnualMesesResponse,
             summary="Comparar movimientos mensuales al mismo día contra el año anterior")
def consultar_comparativa_anual_meses(
    body: ConsultaComparativaAnualMeses,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ComparativaCuentasService = Depends(get_comparativa_cuentas_service),
) -> ComparativaAnualMesesResponse:
    return service.consultar(body)
