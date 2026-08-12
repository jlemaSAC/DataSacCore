from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.analytic.inversiones.dependencies import get_reporte_inversiones_service
from app.modules.analytic.inversiones.schemas import ReporteInversionesRangoResponse
from app.modules.analytic.inversiones.service import ReporteInversionesService
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(tags=["Analytic Sac - Depósitos a Plazos"])


@router.get(
    "/depositos-a-plazos-historico",
    response_model=ReporteInversionesRangoResponse,
    summary="Consultar depósitos a plazos históricos por rango de meses",
    description="""
Consulta los meses cerrados en MongoDB. Si falta un mes cerrado, solicita una
carga única al ETL usando su último día calendario; el SP determina el corte
operativo válido. Si el rango incluye la fecha actual del sistema, ese corte se
consulta directamente desde SQL Server y no se registra como cierre mensual.
""",
)
def obtener_reporte_inversiones(
    fecha_desde: Annotated[
        date,
        Query(description="Fecha inicial en formato YYYY-MM-DD.", examples=["2025-01-01"]),
    ],
    fecha_hasta: Annotated[
        date,
        Query(description="Fecha final en formato YYYY-MM-DD.", examples=["2025-12-31"]),
    ],
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ReporteInversionesService = Depends(get_reporte_inversiones_service),
) -> ReporteInversionesRangoResponse:
    if fecha_hasta < fecha_desde:
        raise HTTPException(status_code=422, detail="fecha_hasta no puede ser menor que fecha_desde.")
    return service.obtener_por_rango(fecha_desde, fecha_hasta, auth_context)
