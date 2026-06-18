from fastapi import APIRouter

from app.modules.analytic.indicadores_financieros.calidad_de_activos.router import (
    router as calidad_de_activos_router,
)
from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.router import (
    router as indicadores_de_liquidez_router,
)
from app.modules.analytic.indicadores_financieros.solvencia.router import (
    router as solvencia_router,
)
from app.modules.analytic.menu.router import router as menu_router


router = APIRouter(prefix="/analytic")

router.include_router(menu_router)
router.include_router(calidad_de_activos_router)
router.include_router(indicadores_de_liquidez_router)
router.include_router(solvencia_router)
