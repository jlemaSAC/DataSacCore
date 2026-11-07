from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.dependencies import (
    get_resumen_ahorro_vista_service,
)
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.schemas import (
    InputResumenAhorroVista,
    ResumenAhorroVistaResponse,
)
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.service import ResumenAhorroVistaService


router = APIRouter(prefix="/ahorro-vista", tags=["Negocios - Ahorro Vista"])


@router.post(
    "/resumen-ahorro-vista", response_model=ResumenAhorroVistaResponse,
    summary="Saldo, cuentas y tasa promedio de ahorros",
    description=(
        "Saldo al corte final del rango (mismo mes), comparado con el cierre del mes "
        "anterior y el 31 de diciembre del año anterior, como en DPF. Incluye cuentas "
        "activas, inactivas y bloqueadas filtradas por es_programado (false por defecto; "
        "true para ahorro restringido), excluyendo aportaciones (tipo 001). "
        "Tasa ponderada por cuentas. Usa SQL para el corte seleccionado y "
        "Mongo para cierres comparativos; reconstruye en SQL si no hay un corte Mongo "
        "completo. Incluye saldo_diario para cada fecha del rango, con el mismo filtro "
        "de agencias y es_programado de la consulta. Un comparativo o día sin cierre disponible "
        "es null, no cero."
    ),
)
def obtener_resumen_ahorro_vista(
    body: InputResumenAhorroVista,
    auth: AuthContext = Depends(get_current_auth_context),
    service: ResumenAhorroVistaService = Depends(get_resumen_ahorro_vista_service),
) -> ResumenAhorroVistaResponse:
    return service.obtener_resumen(body, auth)
