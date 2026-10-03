from fastapi import APIRouter

from app.modules.negocios.colocacion.resumen.router import router as colocacion_resumen_router
from app.modules.negocios.cartera_de_credito.resumen_actual.router import (
    router as cartera_resumen_actual_router,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.router import (
    router as situacion_crediticia_asesores_router,
)
from app.modules.negocios.cartera_de_credito.matriz_transicion.router import (
    router as matriz_transicion_router,
)
from app.modules.negocios.recuperacion.evaluacion_recuperacion.router import (
    router as evaluacion_recuperacion_router,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.router import (
    router as recaudacion_acumulada_router,
)
from app.modules.negocios.recuperacion.resumen_recuperacion.router import (
    router as resumen_recuperacion_router,
)


router = APIRouter(prefix="/negocios")
router.include_router(cartera_resumen_actual_router)
router.include_router(situacion_crediticia_asesores_router)
router.include_router(matriz_transicion_router)
router.include_router(colocacion_resumen_router)
router.include_router(evaluacion_recuperacion_router)
router.include_router(recaudacion_acumulada_router)
router.include_router(resumen_recuperacion_router)
