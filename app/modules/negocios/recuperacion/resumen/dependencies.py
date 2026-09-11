from fastapi import Depends

from app.modules.analytic.recuperacion.recuperacion_historico.dependencies import (
    get_recuperacion_historico_service,
)
from app.modules.analytic.recuperacion.recuperacion_historico.service import (
    RecuperacionHistoricoService,
)
from app.modules.negocios.recuperacion.resumen.service import ResumenRecuperacionService


def get_resumen_recuperacion_service(
    recuperacion_historico_service: RecuperacionHistoricoService = Depends(
        get_recuperacion_historico_service
    ),
) -> ResumenRecuperacionService:
    return ResumenRecuperacionService(recuperacion_historico_service)
