from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.depositos_a_plazos.evaluacion_captadores.dependencies import get_evaluacion_captadores_service
from app.modules.negocios.depositos_a_plazos.evaluacion_captadores.schemas import EvaluacionCaptadoresRequest, EvaluacionCaptadoresResponse
from app.modules.negocios.depositos_a_plazos.evaluacion_captadores.service import EvaluacionCaptadoresService


router = APIRouter(prefix="/depositos-a-plazos", tags=["Negocios - Depósitos a plazos"])


@router.post(
    "/evaluacion-captadores", response_model=EvaluacionCaptadoresResponse,
    summary="Evaluación de captadores frente al cierre del mes anterior",
    description=(
        "Incluye DPF activos, exigibles y vencidos. Tasas por operación de TASA + VARIACION_TASA. "
        "La tasa de renovación incluye nuevos y renovados ingresados entre fecha_inicio y el corte final; "
        "en el cierre anterior corresponde a los ingresados durante ese mes. "
        "Las variaciones de tasas son puntos porcentuales. id_agencia=0 consulta el consolidado."
    ),
)
def obtener_evaluacion_captadores(
    body: EvaluacionCaptadoresRequest,
    auth: AuthContext = Depends(get_current_auth_context),
    service: EvaluacionCaptadoresService = Depends(get_evaluacion_captadores_service),
) -> EvaluacionCaptadoresResponse:
    return service.obtener(body, auth)
