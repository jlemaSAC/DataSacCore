from datetime import date
from typing import Literal

from pydantic import Field

from ..schemas import (
    ConsultaCuentas,
    ConsultaCuentasResponse,
    CuentaDetalle,
    DetalleCuentasPaginacion,
    FiltrosDetalleCuentas,
)


PlazoInactivacion = Literal["0_7", "8_15", "16_30", "cumplido"]


class ConsultaCuentasPorInactivarse(ConsultaCuentas):
    plazos: list[PlazoInactivacion] = Field(
        default_factory=list, max_length=4,
        description="Días hasta cumplir el plazo. Sin selección, incluye todos los rangos.",
    )


class ConsultaCuentasPorInactivarseResponse(ConsultaCuentasResponse):
    pass


class DetalleCuentasPorInactivarseRequest(ConsultaCuentasPorInactivarse, FiltrosDetalleCuentas):
    pass


class CuentaPorInactivarseDetalle(CuentaDetalle):
    ultima_transaccion_activa: date
    fecha_cumplimiento: date
    dias_restantes: int


class DetalleCuentasPorInactivarseResponse(DetalleCuentasPaginacion):
    filas: list[CuentaPorInactivarseDetalle]
