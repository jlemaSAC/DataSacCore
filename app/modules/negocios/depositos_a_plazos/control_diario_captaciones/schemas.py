from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ControlDiarioCaptacionesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date = Field(ge=date(1900, 1, 1), le=date(9998, 12, 31))
    fecha_fin: date = Field(ge=date(1900, 1, 1), le=date(9998, 12, 31))
    id_agencia: int = Field(default=0, ge=0, description="0 para consolidado.")

    @model_validator(mode="after")
    def validar_rango(self) -> "ControlDiarioCaptacionesRequest":
        if self.fecha_inicio > self.fecha_fin:
            raise ValueError("fecha_inicio no puede ser posterior a fecha_fin.")
        if (self.fecha_inicio.year, self.fecha_inicio.month) != (
            self.fecha_fin.year, self.fecha_fin.month
        ):
            raise ValueError("fecha_inicio y fecha_fin deben pertenecer al mismo mes.")
        return self


class CaptacionesDia(BaseModel):
    nuevo: float = 0
    renovado: float = 0


class ControlDiarioCaptacionesFila(BaseModel):
    codigo_usuario: str
    nombre_captador: str
    cargo: str
    id_agencia: int
    agencia: str
    valores: list[CaptacionesDia]


class ControlDiarioCaptacionesResponse(ControlDiarioCaptacionesRequest):
    fecha_corte: date
    dias: list[date]
    filas: list[ControlDiarioCaptacionesFila]
