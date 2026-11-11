from fastapi import APIRouter

from app.modules.analytic.analisis_contable.cuentas_contables.router import router as cuentas_contables_router

router = APIRouter(prefix="/analisis-contable")
router.include_router(cuentas_contables_router)
