from datetime import date

from pydantic import BaseModel, Field, model_validator


class InputResumenColocacion(BaseModel):
    agencias: list[str] = Field(min_length=1, examples=[["MATRIZ", "CUENCA"]])
    fecha_inicio: date = Field(examples=["2026-08-01"])
    fecha_fin: date = Field(examples=["2026-08-31"])

    @model_validator(mode="after")
    def validar_rango(self) -> "InputResumenColocacion":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio.")
        if any(not agencia.strip() for agencia in self.agencias):
            raise ValueError("agencias no puede contener nombres vacíos.")
        return self


class FilaComparativaColocacion(BaseModel):
    agencia: str
    condicion: str
    tipo_prestamo: str
    producto: str
    segmento: str
    asesor: str
    tasa_valor: float | None
    tasa_real: str
    monto_colocado: float
    monto_colocado_periodo_anterior: float
    monto_mismo_rango_mes_anterior: float
    variacion_valor: float


class ResumenColocacionResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    fecha_inicio_periodo_anterior: date
    fecha_fin_periodo_anterior: date
    fecha_inicio_mismo_rango_mes_anterior: date
    fecha_fin_mismo_rango_mes_anterior: date
    agrupaciones: list[FilaComparativaColocacion]
