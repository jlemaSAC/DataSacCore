from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.modules.analytic.spread_tasa.historico_schemas import CorteHistorico, HistoricoSpreadInput

IndicadorSpread = Literal['costo_promedio_fondeo', 'rendimiento_cartera_por_vencer', 'spread_tasa']


class HistoricoSpreadTasaInput(HistoricoSpreadInput):
    pass


class ComponenteTasa(BaseModel):
    intereses: float | None = None
    saldo_promedio: float | None = None
    valor: float | None = None


class ComponentesSpread(BaseModel):
    rendimiento_cartera_por_vencer: ComponenteTasa
    costo_promedio_fondeo: ComponenteTasa


class SpreadHistoricoItem(BaseModel):
    periodo: str
    fecha_corte: date
    fecha_promedio_desde: date
    id_agencia: int
    indicador: IndicadorSpread
    intereses: float | None
    saldo_promedio: float | None
    valor: float | None
    cierres_con_datos: int
    componentes: ComponentesSpread | None = None


class HistoricoSpreadTasaResponse(BaseModel):
    cortes: list[CorteHistorico]
    datos: list[SpreadHistoricoItem]
