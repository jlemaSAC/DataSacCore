from fastapi import Depends

from app.modules.analytic.colocacion.colocacion_historico.dependencies import (
    get_colocacion_historico_service,
)
from app.modules.analytic.colocacion.colocacion_historico.service import ColocacionHistoricoService
from app.modules.negocios.colocacion.resumen.service import ResumenColocacionService


def get_resumen_colocacion_service(
    colocacion_historico_service: ColocacionHistoricoService = Depends(
        get_colocacion_historico_service
    ),
) -> ResumenColocacionService:
    return ResumenColocacionService(colocacion_historico_service)
