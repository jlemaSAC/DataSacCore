from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ControlDiarioCancelacionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date = Field(ge=date(1900, 1, 1), le=date(9998, 12, 31))
    fecha_fin: date = Field(ge=date(1900, 1, 1), le=date(9998, 12, 31))
    id_agencia: int = Field(default=0, ge=0, description="0 para consolidado.")

    @model_validator(mode="after")
    def validar_rango(self) -> "ControlDiarioCancelacionRequest":
        if self.fecha_inicio > self.fecha_fin:
            raise ValueError("fecha_inicio no puede ser posterior a fecha_fin.")
        if (self.fecha_inicio.year, self.fecha_inicio.month) != (
            self.fecha_fin.year, self.fecha_fin.month
        ):
            raise ValueError("fecha_inicio y fecha_fin deben pertenecer al mismo mes.")
        return self


class CancelacionDia(BaseModel):
    nuevo: float = 0
    renovado: float = 0


class ControlDiarioCancelacionFila(BaseModel):
    codigo_usuario: str
    nombre_captador: str
    cargo: str
    id_agencia: int
    agencia: str
    valores: list[CancelacionDia]


class ControlDiarioCancelacionResponse(ControlDiarioCancelacionRequest):
    fecha_corte: date
    dias: list[date]
    filas: list[ControlDiarioCancelacionFila]


class DetalleControlCancelacionRequest(ControlDiarioCancelacionRequest):
    fecha: date | None = Field(default=None, description="Día seleccionado; null consulta todo el rango.")
    codigo_usuario: str | None = Field(default=None, max_length=100)
    cargos: list[str] = Field(default_factory=list, max_length=100)
    condicion: Literal["todas", "nuevo", "renovado"] = "todas"

    @field_validator("codigo_usuario")
    @classmethod
    def normalizar_codigo(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("codigo_usuario no puede estar vacío.")
        return value.strip()

    @field_validator("cargos")
    @classmethod
    def normalizar_cargos(cls, value: list[str]) -> list[str]:
        if any(not cargo.strip() for cargo in value):
            raise ValueError("cargos no puede contener valores vacíos.")
        return list(dict.fromkeys(cargo.strip().upper() for cargo in value))

    @model_validator(mode="after")
    def validar_dia(self) -> "DetalleControlCancelacionRequest":
        if self.fecha is not None and not self.fecha_inicio <= self.fecha <= self.fecha_fin:
            raise ValueError("fecha debe estar dentro del rango consultado.")
        return self


class DetalleControlCancelacionFila(BaseModel):
    id_deposito: int
    numero_cliente: str
    nombre_cliente: str
    agencia: str
    captador: str
    numero_deposito: str
    monto: float
    interes_total: float = Field(description="Interés calculado total al corte, incluyendo el ya pagado.")
    tasa_total: float = Field(description="Tasa del DPF al corte; suma TASA y VARIACION_TASA una sola vez.")
    tiene_prestamo: bool
    fecha_vencimiento: date
    fecha_cancelacion: date
    estado: str


class DetalleControlCancelacionResponse(DetalleControlCancelacionRequest):
    fecha_corte: date
    total_registros: int
    total_monto: float
    total_interes: float
    items: list[DetalleControlCancelacionFila]
