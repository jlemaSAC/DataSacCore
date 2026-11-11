from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.dependencies import get_resultados_ejercicio_service
from app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.schemas import (
    ConsultaCorteResultados, ConsultaHistoricoResultados, ResultadosEjercicioResponse,
)
from app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.service import ResultadosEjercicioService

router = APIRouter(prefix="/resumen-resultados-del-ejercicio", tags=["Analytic Sac - Análisis Contable"])


@router.post("/fecha-corte", response_model=ResultadosEjercicioResponse, summary="Estado de resultados a fecha de corte")
def consultar_corte(body: ConsultaCorteResultados,
                    auth_context: AuthContext = Depends(get_current_auth_context),
                    service: ResultadosEjercicioService = Depends(get_resultados_ejercicio_service)) -> ResultadosEjercicioResponse:
    return service.consultar_corte(body)


@router.post("/historico-mensual", response_model=ResultadosEjercicioResponse, summary="Estado de resultados por cierre mensual")
def consultar_mensual(body: ConsultaHistoricoResultados,
                      auth_context: AuthContext = Depends(get_current_auth_context),
                      service: ResultadosEjercicioService = Depends(get_resultados_ejercicio_service)) -> ResultadosEjercicioResponse:
    return service.consultar_mensual(body)


@router.post("/historico-diario", response_model=ResultadosEjercicioResponse, summary="Estado de resultados por día")
def consultar_diario(body: ConsultaHistoricoResultados,
                     auth_context: AuthContext = Depends(get_current_auth_context),
                     service: ResultadosEjercicioService = Depends(get_resultados_ejercicio_service)) -> ResultadosEjercicioResponse:
    return service.consultar_diario(body)
