from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.modules.analytic.spread_tasa.historico_schemas import CorteHistorico, HistoricoSpreadInput

Producto = Literal['microcredito', 'consumo', 'inmobiliario', 'cartera']


class HistoricoRendimientosInput(HistoricoSpreadInput):
    pass


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
