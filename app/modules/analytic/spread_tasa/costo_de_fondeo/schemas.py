from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.modules.analytic.spread_tasa.historico_schemas import CorteHistorico, HistoricoSpreadInput

TipoCosto = Literal['ahorro_plazo', 'ahorro_vista', 'obligaciones_financieras', 'promedio_fondeo']


class CostoFondeoInput(HistoricoSpreadInput):
    pass


class CostoHistoricoItem(BaseModel):
    periodo: str
    fecha_corte: date
    fecha_promedio_desde: date
    id_agencia: int
    tipo_costo: TipoCosto
    intereses: float | None
    saldo_promedio: float | None
    costo: float | None
    cierres_con_datos: int


class CostoFondeoResponse(BaseModel):
    cortes: list[CorteHistorico]
    datos: list[CostoHistoricoItem]
