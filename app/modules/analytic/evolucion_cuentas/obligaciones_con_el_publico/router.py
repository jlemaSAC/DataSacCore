from fastapi import APIRouter, Depends

from app.modules.analytic.evolucion_cuentas.obligaciones_con_el_publico.dependencies import (
    get_evolucion_obligaciones_con_el_publico_service,
    get_historico_obligaciones_con_el_publico_service,
)
from app.modules.analytic.evolucion_cuentas.obligaciones_con_el_publico.schemas import (
    EvolucionObligacionesConElPublicoResponse,
    HistoricoObligacionesConElPublicoResponse,
)
from app.modules.analytic.evolucion_cuentas.obligaciones_con_el_publico.service import (
    EvolucionObligacionesConElPublicoService,
    HistoricoObligacionesConElPublicoService,
)
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import ConsultaEvolucionBalance
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import ConsultaVariacion
from app.modules.auth.dependencies import get_current_auth_context

router = APIRouter(
    tags=["Analytic Sac - Evolución de cuentas"],
    dependencies=[Depends(get_current_auth_context)],
)


@router.post("/evolucion-obligaciones-con-el-publico", response_model=EvolucionObligacionesConElPublicoResponse)
def consultar_evolucion_obligaciones_con_el_publico(
    body: ConsultaEvolucionBalance,
    service: EvolucionObligacionesConElPublicoService = Depends(get_evolucion_obligaciones_con_el_publico_service),
):
    return service.consultar(body)


@router.post("/variacion-obligaciones-con-el-publico", response_model=HistoricoObligacionesConElPublicoResponse)
@router.post("/historico-obligaciones-con-el-publico", response_model=HistoricoObligacionesConElPublicoResponse, include_in_schema=False)
def consultar_historico_obligaciones_con_el_publico(
    body: ConsultaVariacion,
    service: HistoricoObligacionesConElPublicoService = Depends(get_historico_obligaciones_con_el_publico_service),
):
    return service.consultar(body)
