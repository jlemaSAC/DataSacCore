from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.cartera_de_credito.cartera_improductiva.dependencies import (
    get_cartera_improductiva_service,
)
from app.modules.negocios.cartera_de_credito.cartera_improductiva.schemas import (
    CarteraImproductivaRequest,
    CarteraImproductivaResponse,
    CarteraImproductivaPrestamosRequest,
    CarteraImproductivaPrestamosResponse,
)
from app.modules.negocios.cartera_de_credito.cartera_improductiva.service import (
    CarteraImproductivaService,
)


router = APIRouter(
    prefix="/cartera-de-credito",
    tags=["Negocios - Cartera de credito"],
)


@router.post(
    "/cartera-improductiva",
    response_model=CarteraImproductivaResponse,
    summary="Comparar cartera improductiva y morosidad de asesores",
    description=(
        "Compara fecha_fin, fecha_inicio, el día anterior a fecha_fin "
        "y las fechas equivalentes de inicio y fin del mes anterior. "
        "id_agencia=0 devuelve el consolidado de todas las agencias."
    ),
)
def obtener_cartera_improductiva(
    request: CarteraImproductivaRequest,
    _: AuthContext = Depends(get_current_auth_context),
    service: CarteraImproductivaService = Depends(
        get_cartera_improductiva_service
    ),
) -> CarteraImproductivaResponse:
    return service.obtener(
        fecha_inicio=request.fecha_inicio,
        fecha_fin=request.fecha_fin,
        id_agencia=request.id_agencia,
        filtrar_diferidos=request.filtrar_diferidos,
    )


@router.post(
    "/cartera-improductiva/prestamos",
    response_model=CarteraImproductivaPrestamosResponse,
    summary="Consultar préstamos de los grupos de cartera improductiva seleccionados",
)
def obtener_prestamos_cartera_improductiva(
    request: CarteraImproductivaPrestamosRequest,
    _: AuthContext = Depends(get_current_auth_context),
    service: CarteraImproductivaService = Depends(get_cartera_improductiva_service),
) -> CarteraImproductivaPrestamosResponse:
    return service.obtener_prestamos(request)
