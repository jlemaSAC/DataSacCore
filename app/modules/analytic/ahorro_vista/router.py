from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.analytic.ahorro_vista.dependencies import get_reporte_ahorro_vista_service
from app.modules.analytic.ahorro_vista.schemas import ReporteAhorroVistaRangoResponse
from app.modules.analytic.ahorro_vista.service import ReporteAhorroVistaService
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext


router = APIRouter(tags=["Analytic Sac - Ahorro a la vista"])


@router.get(
    "/ahorros-vista-historico",
    response_model=ReporteAhorroVistaRangoResponse,
    summary="Consultar saldos de ahorros a la vista por rango de meses",
    description=(
        "Consulta directamente SQL Server para evaluación. Los meses históricos "
        "se reconstruyen con los cierres de vista y colocación; no usa ETL ni MongoDB."
    ),
)
def obtener_reporte_ahorro_vista(
    fecha_desde: Annotated[
        date,
        Query(description="Fecha inicial en formato YYYY-MM-DD.", examples=["2025-01-01"]),
    ],
    fecha_hasta: Annotated[
        date,
        Query(description="Fecha final en formato YYYY-MM-DD.", examples=["2025-12-31"]),
    ],
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: ReporteAhorroVistaService = Depends(get_reporte_ahorro_vista_service),
) -> ReporteAhorroVistaRangoResponse:
    if fecha_hasta < fecha_desde:
        raise HTTPException(status_code=422, detail="fecha_hasta no puede ser menor que fecha_desde.")
    return service.obtener_por_rango(fecha_desde, fecha_hasta, auth_context)
