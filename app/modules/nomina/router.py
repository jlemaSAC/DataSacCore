from fastapi import APIRouter

from app.modules.nomina.cargos.router import router as cargos_router


router = APIRouter(prefix="/nomina")
router.include_router(cargos_router)
