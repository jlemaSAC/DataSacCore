from fastapi import APIRouter

from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.router import router as balance_router

router = APIRouter(prefix="/evolucion-de-cuentas")
router.include_router(balance_router)
