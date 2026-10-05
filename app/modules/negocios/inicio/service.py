from typing import Any

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.inicio.schemas import (
    InicioCarteraCredito,
    InicioColocacion,
    NegocioInicioResponse,
)


class NegocioInicioService:
    def __init__(self, colocacion_service: Any, cartera_service: Any) -> None:
        self.colocacion_service = colocacion_service
        self.cartera_service = cartera_service

    def obtener(
        self,
        *,
        id_agencia: int,
        auth_context: AuthContext,
    ) -> NegocioInicioResponse:
        colocacion = self.colocacion_service.obtener(
            id_agencia=id_agencia,
            auth_context=auth_context,
        )
        cartera = self.cartera_service.obtener(
            id_agencia=id_agencia,
            auth_context=auth_context,
        )
        return NegocioInicioResponse(
            fecha=colocacion.fecha,
            fecha_ayer=colocacion.fecha_ayer,
            id_agencia=id_agencia,
            agencia=cartera.agencia,
            colocacion=InicioColocacion(
                resumen=colocacion.resumen,
                asesores=colocacion.asesores,
            ),
            cartera_de_credito=InicioCarteraCredito(
                resumen=cartera.resumen,
                asesores=cartera.asesores,
            ),
        )
