from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.analytic.analisis_contable.resumen_balance_de_resultados.dependencies import get_balance_resultados_service
from app.modules.analytic.analisis_contable.resumen_balance_de_resultados.schemas import ConsultaBalanceResultados, ResumenBalanceResultados
from app.modules.analytic.analisis_contable.resumen_balance_de_resultados.service import BalanceResultadosService

router = APIRouter(tags=["Analytic Sac - Análisis Contable"])


@router.post("/resumen-balance-de-resultados", response_model=ResumenBalanceResultados,
             summary="Consultar ingresos, gastos, márgenes y utilidad a una fecha de corte")
def consultar_balance_resultados(
    body: ConsultaBalanceResultados,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: BalanceResultadosService = Depends(get_balance_resultados_service),
) -> ResumenBalanceResultados:
    return service.consultar(body)
