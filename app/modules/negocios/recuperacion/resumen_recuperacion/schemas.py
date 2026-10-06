from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InputResumenRecuperacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date
    fecha_fin: date
    agencias: list[str] = Field(default_factory=list)

    @field_validator("agencias")
    @classmethod
    def normalizar_agencias(cls, valores: list[str]) -> list[str]:
        agencias = [valor.strip().upper() for valor in valores]
        if any(not valor for valor in agencias):
            raise ValueError("Las agencias no pueden contener valores vacíos.")
        return list(dict.fromkeys(agencias))

    @model_validator(mode="after")
    def validar_rango(self) -> "InputResumenRecuperacion":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio.")
        if (self.fecha_inicio.year, self.fecha_inicio.month) != (
            self.fecha_fin.year, self.fecha_fin.month
        ):
            raise ValueError("El rango de consulta debe estar dentro del mismo mes.")
        return self


class RangoResumenRecuperacion(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    recuperacion_total: float
    recuperacion_por_tipo: dict[str, float]


class DiaResumenRecuperacion(BaseModel):
    fecha: date
    recuperacion_total: float
    recuperacion_por_tipo: dict[str, float]


class ResumenActualRecuperacionResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    consolidado: bool
    agencias: list[str]
    actual: RangoResumenRecuperacion
    mes_anterior: RangoResumenRecuperacion
    anio_anterior: RangoResumenRecuperacion


class ResumenRecuperacionResponse(ResumenActualRecuperacionResponse):
    diario: list[DiaResumenRecuperacion]
