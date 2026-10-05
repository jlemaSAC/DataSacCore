from fastapi import Depends

from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.dependencies import (
    get_resumen_diario_cartera_service,
)
from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.service import (
    ResumenDiarioCarteraService,
)
from app.modules.negocios.colocacion.diaria_asesores.dependencies import (
    get_colocacion_diaria_asesores_service,
)
from app.modules.negocios.colocacion.diaria_asesores.service import (
    ColocacionDiariaAsesoresService,
)
from app.modules.negocios.inicio.service import NegocioInicioService


def get_negocio_inicio_service(
    colocacion_service: ColocacionDiariaAsesoresService = Depends(
        get_colocacion_diaria_asesores_service
    ),
    cartera_service: ResumenDiarioCarteraService = Depends(
        get_resumen_diario_cartera_service
    ),
) -> NegocioInicioService:
    return NegocioInicioService(
        colocacion_service=colocacion_service,
        cartera_service=cartera_service,
    )
