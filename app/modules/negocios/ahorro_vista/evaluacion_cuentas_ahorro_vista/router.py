from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.ahorro_vista.evaluacion_cuentas_ahorro_vista.dependencies import (
    get_evaluacion_cuentas_ahorro_vista_service,
)
from app.modules.negocios.ahorro_vista.evaluacion_cuentas_ahorro_vista.schemas import (
    EvaluacionCuentasAhorroVistaRequest,
    EvaluacionCuentasAhorroVistaResponse,
)
from app.modules.negocios.ahorro_vista.evaluacion_cuentas_ahorro_vista.service import (
    EvaluacionCuentasAhorroVistaService,
)


router = APIRouter(prefix="/ahorro-vista", tags=["Negocios - Ahorro Vista"])


@router.post(
    "/evaluacion-cuentas-ahorro-vista", response_model=EvaluacionCuentasAhorroVistaResponse,
    summary="Evaluación de cuentas de ahorro frente al cierre del mes anterior",
    description=(
        "Saldo, cuentas y tasa promedio por asesor, agencia y producto de ahorro. "
        "Incluye estados A/I/B y excluye aportaciones (001). es_programado=false "
        "por defecto; true para cuentas restringidas. "
        "Compara el corte final con el cierre del mes anterior; fecha_inicio no limita "
        "la apertura de cuentas. id_agencia=0 consulta el consolidado. "
        "ProductoAhorro y CodigoProducto permiten filtrar después de cargar los datos. "
        "Reagrupar la tasa como SUM(SumaTasas)/SUM(Cuentas); las diferencias son puntos "
        "porcentuales. Los grupos ausentes son null y un cierre no disponible devuelve 404."
    ),
)
def obtener_evaluacion_cuentas_ahorro_vista(
    body: EvaluacionCuentasAhorroVistaRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: EvaluacionCuentasAhorroVistaService = Depends(get_evaluacion_cuentas_ahorro_vista_service),
) -> EvaluacionCuentasAhorroVistaResponse:
    return service.obtener(body, auth)
