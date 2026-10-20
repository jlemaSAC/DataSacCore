from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


TipoVariacionCartera = Literal['diaria', 'cierre_mes_anterior', 'mismo_dia_mes_anterior']


class ControlDiarioCarteraRequest(BaseModel):
    fecha_inicio: date = Field(
        ge=date(1900, 1, 1), le=date(9998, 12, 31), description="Inicio inclusivo en formato YYYY-MM-DD.",
    )
    fecha_fin: date = Field(
        ge=date(1900, 1, 1), le=date(9998, 12, 31), description="Fin inclusivo en formato YYYY-MM-DD.",
    )
    agencia: str | None = Field(default=None, max_length=150)
    filtrar_diferidos: bool | None = None
    tipo_variacion: TipoVariacionCartera = Field(
        default='diaria',
        description='Base de comparación. El mismo día se ajusta al último día válido del mes anterior.',
    )

    @field_validator("agencia")
    @classmethod
    def limpiar_agencia(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class VariacionCarteraValores(BaseModel):
    saldo_capital: float
    cartera_improductiva: float
    provisiones: float


class DiaControlCartera(BaseModel):
    fecha: date
    fecha_anterior: date
    disponible: bool = Field(description="Existen ambos cortes necesarios para calcular la variación.")


class FilaControlDiarioCartera(BaseModel):
    codigo_asesor: str
    nombre_asesor: str
    cargo: str
    agencia: str
    variaciones: list[VariacionCarteraValores | None]


class ControlDiarioCarteraResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    agencia: str | None
    filtrar_diferidos: bool | None
    tipo_variacion: TipoVariacionCartera
    dias: list[DiaControlCartera]
    filas: list[FilaControlDiarioCartera]
