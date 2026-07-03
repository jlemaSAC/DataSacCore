from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.prestamos.dependencies import get_universo_prestamos_service
from app.modules.prestamos.schemas import (
    PrestamoUniverseRequest,
    UniversoPrestamosBuscarResponse,
)
from app.modules.prestamos.service import UniversoPrestamosService


router = APIRouter(prefix="/prestamos", tags=["Prestamos"])


@router.post(
    "/universo/buscar",
    response_model=UniversoPrestamosBuscarResponse,
    summary="Buscar prestamos del universo central en Mongo actual e historico",
)
def buscar_universo_prestamos(
    body: PrestamoUniverseRequest,
    auth_context: AuthContext = Depends(get_current_auth_context),
    service: UniversoPrestamosService = Depends(get_universo_prestamos_service),
) -> UniversoPrestamosBuscarResponse:
    return service.buscar_universo(filtros=body, auth_context=auth_context)
