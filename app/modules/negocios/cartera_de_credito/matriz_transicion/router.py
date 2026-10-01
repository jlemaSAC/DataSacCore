from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.matriz_transicion.dependencies import (
    get_matriz_transicion_prestamos_service,
    get_matriz_transicion_service,
)
from app.modules.negocios.cartera_de_credito.matriz_transicion.schemas import (
    MatrizTransicionFiltrosRequest,
    MatrizTransicionFiltrosResponse,
    MatrizTransicionPrestamosRequest,
    MatrizTransicionRequest,
    MatrizTransicionResponse,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.schemas import (
    PrestamoRecaudadoAcumulado,
)
from app.modules.negocios.cartera_de_credito.matriz_transicion.service import MatrizTransicionService


router = APIRouter(prefix="/cartera-de-credito", tags=["Negocios - Cartera de credito"])


@router.post(
    "/matriz-transicion/filtros",
    response_model=MatrizTransicionFiltrosResponse,
    summary="Catálogos de filtros disponibles para un corte de matriz de transición",
)
def obtener_filtros_matriz_transicion(
    request: MatrizTransicionFiltrosRequest,
    _: AuthContext = Depends(get_current_auth_context),
    service: MatrizTransicionService = Depends(get_matriz_transicion_service),
) -> MatrizTransicionFiltrosResponse:
    """Devuelve asesores, cargos y estados encontrados en el corte indicado."""
    return service.obtener_filtros(request)


@router.post(
    "/matriz-transicion",
    response_model=MatrizTransicionResponse,
    summary="Matriz de transición entre dos cortes seleccionados",
)
def obtener_matriz_transicion_tiempo_real(
    request: MatrizTransicionRequest,
    _: AuthContext = Depends(get_current_auth_context),
    service: MatrizTransicionService = Depends(get_matriz_transicion_service),
) -> MatrizTransicionResponse:
    """Compara fecha_corte_anterior contra fecha_corte_nuevo."""
    return service.obtener(request)


@router.post(
    "/matriz-transicion/prestamos",
    response_model=list[PrestamoRecaudadoAcumulado],
    summary="Préstamos de una transición específica entre dos cortes",
)
def obtener_prestamos_por_transicion(
    request: MatrizTransicionPrestamosRequest,
    _: AuthContext = Depends(get_current_auth_context),
    service: MatrizTransicionService = Depends(get_matriz_transicion_prestamos_service),
) -> list[PrestamoRecaudadoAcumulado]:
    """Filtra una celda origen-destino de la matriz, sin paginación."""
    return service.obtener_prestamos(request)
