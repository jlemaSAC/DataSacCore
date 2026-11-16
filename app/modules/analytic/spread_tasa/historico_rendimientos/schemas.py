from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field

Producto = Literal['microcredito', 'consumo', 'inmobiliario', 'cartera']


class HistoricoRendimientosInput(BaseModel):
    periodo_desde: str = Field(pattern=r'^[1-9]\d{3}-(0[1-9]|1[0-2])$')
    periodo_hasta: str = Field(pattern=r'^[1-9]\d{3}-(0[1-9]|1[0-2])$')
    ids_agencia: list[Annotated[int, Field(ge=0)]] = Field(default_factory=lambda: [0], min_length=1, max_length=100)


class CorteHistorico(BaseModel):
    periodo: str
    fecha_corte: date
    parcial: bool


class RendimientoHistoricoItem(BaseModel):
    periodo: str
    fecha_corte: date
    fecha_promedio_desde: date
    id_agencia: int
    producto: Producto
    intereses: float | None
    saldo_promedio: float | None
    rendimiento: float | None
    cierres_con_datos: int


class HistoricoRendimientosResponse(BaseModel):
    cortes: list[CorteHistorico]
    datos: list[RendimientoHistoricoItem]
