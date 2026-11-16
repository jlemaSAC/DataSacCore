from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field


class HistoricoSpreadInput(BaseModel):
    periodo_desde: str = Field(pattern=r'^[1-9]\d{3}-(0[1-9]|1[0-2])$')
    periodo_hasta: str = Field(pattern=r'^[1-9]\d{3}-(0[1-9]|1[0-2])$')
    ids_agencia: list[Annotated[int, Field(ge=0)]] = Field(
        default_factory=lambda: [0], min_length=1, max_length=100,
    )


class CorteHistorico(BaseModel):
    periodo: str
    fecha_corte: date
    parcial: bool
