from fastapi import APIRouter

from app.modules.analytic.analisis_contable.cuentas_contables.router import router as cuentas_contables_router
from app.modules.analytic.analisis_contable.resumen_balance_de_resultados.router import router as balance_resultados_router
from app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.router import router as resultados_ejercicio_router

router = APIRouter(prefix="/analisis-contable")
router.include_router(cuentas_contables_router)
router.include_router(balance_resultados_router)
router.include_router(resultados_ejercicio_router)
