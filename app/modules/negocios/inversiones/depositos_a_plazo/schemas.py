from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InputResumenActualDepositos(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date
    fecha_fin: date
    agencias: list[str] = Field(default_factory=list, description="Vacío consulta el consolidado.")

    @field_validator("agencias")
    @classmethod
    def normalizar_agencias(cls, valores: list[str]) -> list[str]:
        if any(not valor.strip() for valor in valores):
            raise ValueError("agencias no puede contener nombres vacíos.")
        return list(dict.fromkeys(valor.strip().upper() for valor in valores))

    @model_validator(mode="after")
    def validar_rango(self) -> "InputResumenActualDepositos":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio.")
        if (self.fecha_inicio.year, self.fecha_inicio.month) != (
            self.fecha_fin.year, self.fecha_fin.month
        ):
            raise ValueError("fecha_inicio y fecha_fin deben pertenecer al mismo mes.")
        return self


class MetricasDepositos(BaseModel):
    saldo: float
    numero_operaciones: int = Field(ge=0)
    tasa_promedio: float | None
    tasa_promedio_renovacion: float | None = Field(
        description="Promedio por operación de todos los DPF creados en el rango seleccionado."
    )


class IndicadoresDepositos(MetricasDepositos):
    fecha_corte: date


class ComparativoDepositos(BaseModel):
    actual: IndicadoresDepositos | None
    mes_anterior: IndicadoresDepositos | None
    anio_anterior: IndicadoresDepositos | None


class AgenciaResumenDepositos(MetricasDepositos):
    agencia: str


class ResumenActualDepositosResponse(ComparativoDepositos):
    fecha_inicio: date
    fecha_fin: date
    fecha_mes_anterior: date
    fecha_anio_anterior: date
    consolidado: bool
    agencias: list[str]
    por_agencia: list[AgenciaResumenDepositos]
