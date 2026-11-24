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


TiempoInactividad = Literal[
    "0_1", "1_2", "2_3", "3_6", "6_12", "12_24", "24_36", "36_60",
    "mas_60", "mas_36", "sin_fecha"
]


class ConsultaCuentasInactivas(ConsultaCuentas):
    inactividad: TiempoInactividad | list[TiempoInactividad] | None = Field(
        default=None, description="Uno o varios rangos desde la última entrada al estado I."
    )


class DetalleCuentasInactivasRequest(ConsultaCuentasInactivas, FiltrosDetalleCuentas):
    pass


class ConsultaCuentasInactivasResponse(ConsultaCuentasResponse):
    pass


class CuentaInactivaDetalle(CuentaDetalle):
    fecha_inactivacion: date | None
    dias_inactividad: int | None


class DetalleCuentasInactivasResponse(DetalleCuentasPaginacion):
    filas: list[CuentaInactivaDetalle]
