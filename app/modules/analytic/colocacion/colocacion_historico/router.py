from fastapi import APIRouter, Depends

from app.modules.analytic.colocacion.colocacion_historico.dependencies import (
    get_colocacion_historico_service,
)
from app.modules.analytic.colocacion.colocacion_historico.schemas import (
    ColocacionHistoricoRangoResponse,
    InputColocacionHistoricoRango,
    InputSaldoInicialAgencia,
    SaldoInicialAgenciaResponse,
)
from app.modules.analytic.colocacion.colocacion_historico.service import (
    ColocacionHistoricoService,
)
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(tags=["Analytic Sac - Colocacion"])


@router.post(
    "/colocacion/colocacion-historico",
    response_model=SaldoInicialAgenciaResponse,
    summary="Consultar colocación histórica agrupada para dashboards",
)
def obtener_saldo_inicial_agencias_por_mes(
    body: InputSaldoInicialAgencia,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ColocacionHistoricoService = Depends(get_colocacion_historico_service),
) -> SaldoInicialAgenciaResponse:
    return service.obtener_saldo_inicial_agencias_por_mes(
        input_data=body,
        auth_context=auth_context,
    )


@router.post(
    "/colocacion/colocacion-historico/rango",
    response_model=ColocacionHistoricoRangoResponse,
    summary="Consultar colocación histórica por rango de fechas",
    description="""
Divide el rango solicitado en segmentos mensuales y devuelve un resumen por
período `YYYY-MM`, además de las agrupaciones dimensionales para dashboards.

- El rango máximo permitido es de 24 meses.
- `fecha_hasta` no puede superar la fecha del sistema incluida en el token.
- En el mes actual, MongoDB aporta hasta ayer y SQL Server aporta el día actual.
- Para rangos parciales históricos se utiliza como corte Mongo el último día
  efectivo de cada segmento.
""",
)
def obtener_colocacion_historica_por_rango(
    body: InputColocacionHistoricoRango,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ColocacionHistoricoService = Depends(get_colocacion_historico_service),
) -> ColocacionHistoricoRangoResponse:
    return service.obtener_colocacion_historica_por_rango(
        input_data=body,
        auth_context=auth_context,
    )
