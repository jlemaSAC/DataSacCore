from fastapi import APIRouter

from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.router import router as balance_router
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.router import router as variacion_router

from app.modules.analytic.evolucion_cuentas.balance_de_resultados.router import router as resultados_router

from app.modules.analytic.evolucion_cuentas.cartera_de_credito.router import router as cartera_router

from app.modules.analytic.evolucion_cuentas.cartera_por_vencer.router import router as cartera_por_vencer_router

from app.modules.analytic.evolucion_cuentas.obligaciones_con_el_publico.router import router as obligaciones_router

from app.modules.analytic.evolucion_cuentas.depositos_a_plazos.router import router as depositos_plazos_router

from app.modules.analytic.evolucion_cuentas.cartera_no_devenga.router import router as cartera_no_devenga_router

from app.modules.analytic.evolucion_cuentas.cartera_vencida.router import router as cartera_vencida_router

router = APIRouter(prefix="/evolucion-de-cuentas")
router.include_router(balance_router)
router.include_router(variacion_router)
router.include_router(resultados_router)
router.include_router(cartera_router)
router.include_router(cartera_por_vencer_router)
router.include_router(cartera_no_devenga_router)
router.include_router(cartera_vencida_router)
router.include_router(obligaciones_router)
router.include_router(depositos_plazos_router)
