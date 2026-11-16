from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class ResumenSpreadTasaInput(BaseModel):
    fecha_corte: date
    id_agencia: int = Field(default=0, ge=0, description="0 consulta el consolidado contable (agencia 1).")

    @field_validator('fecha_corte')
    @classmethod
    def validar_fecha_corte(cls, fecha: date) -> date:
        if fecha.year == 1:
            raise ValueError('La fecha de corte debe permitir consultar el cierre del año anterior.')
        return fecha


class IndicadoresSpreadTasa(BaseModel):
    costo_ahorro_plazo: float | None
    costo_ahorro_vista: float | None
    costo_obligaciones_financieras: float | None
    costo_promedio_fondeo: float | None
    spread_tasa: float | None
    rendimiento_microcredito_por_vencer: float | None
    rendimiento_credito_consumo_por_vencer: float | None
    rendimiento_cartera_por_vencer: float | None
    inmobiliario_por_vencer: float | None


class ResumenSpreadTasaResponse(BaseModel):
    fecha_corte: date
    fecha_promedio_desde: date
    id_agencia: int
    id_agencia_contable: int
    meses: int
    dias_con_datos: int
    indicadores: IndicadoresSpreadTasa
    saldos_corte: dict[str, float]
    saldos_promedio: dict[str, float]
    costo_fuentes_fondeo_spread: float | None


class SpreadAgenciasInput(BaseModel):
    fecha_corte: date
    ids_agencia: list[Annotated[int, Field(gt=1)]] = Field(min_length=1, max_length=500)

    @field_validator('fecha_corte')
    @classmethod
    def validar_fecha_corte(cls, fecha: date) -> date:
        return ResumenSpreadTasaInput.validar_fecha_corte(fecha)


class SpreadAgenciaItem(BaseModel):
    id_agencia: int
    rendimiento_cartera_por_vencer: float | None
    costo_promedio_fondeo: float | None
    spread_tasa: float | None


class SpreadAgenciasResponse(BaseModel):
    fecha_corte: date
    agencias: list[SpreadAgenciaItem]
