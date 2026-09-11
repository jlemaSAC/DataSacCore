from fastapi import APIRouter

from app.modules.negocios.colocacion.resumen.router import router as colocacion_resumen_router
from app.modules.negocios.recuperacion.resumen.router import router as recuperacion_resumen_router


router = APIRouter(prefix="/negocios")
router.include_router(colocacion_resumen_router)
router.include_router(recuperacion_resumen_router)
