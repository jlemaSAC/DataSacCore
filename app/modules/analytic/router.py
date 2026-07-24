from fastapi import APIRouter

from app.modules.analytic.cartera_de_credito.morosidad_historica.router import (
    router as morosidad_historica_router,
)
from app.modules.analytic.colocacion.colocacion_historico.router import (
    router as colocacion_historico_router,
)
from app.modules.analytic.indicadores_financieros.calidad_de_activos.router import (
    router as calidad_de_activos_router,
)
from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.router import (
    router as indicadores_de_liquidez_router,
)
from app.modules.analytic.indicadores_financieros.indicadores_de_eficiencia.router import (
    router as indicadores_de_eficiencia_router,
)
from app.modules.analytic.indicadores_financieros.rentabilidad.router import (
    router as rentabilidad_router,
)
from app.modules.analytic.indicadores_financieros.solvencia.router import (
    router as solvencia_router,
)
from app.modules.analytic.menu.router import router as menu_router
from app.modules.analytic.recuperacion.recuperacion_historico.router import (
    router as recuperacion_historico_router,
)


router = APIRouter(prefix="/analytic")

router.include_router(menu_router)
router.include_router(morosidad_historica_router)
router.include_router(colocacion_historico_router)
router.include_router(recuperacion_historico_router)
router.include_router(calidad_de_activos_router)
router.include_router(indicadores_de_liquidez_router)
router.include_router(indicadores_de_eficiencia_router)
router.include_router(rentabilidad_router)
router.include_router(solvencia_router)
