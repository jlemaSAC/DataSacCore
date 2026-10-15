from datetime import date

from pydantic import BaseModel, Field, field_validator


class ControlDiarioCarteraRequest(BaseModel):
    mes: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Mes en formato YYYY-MM.")
    agencia: str | None = Field(default=None, max_length=150)
    filtrar_diferidos: bool | None = None

    @field_validator("mes")
    @classmethod
    def validar_mes(cls, value: str) -> str:
        fecha = date.fromisoformat(f"{value}-01")
        if fecha.year < 1900 or fecha.year > 9998:
            raise ValueError("El año debe estar entre 1900 y 9998.")
        return value

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
    mes: str
    agencia: str | None
    filtrar_diferidos: bool | None
    dias: list[DiaControlCartera]
    filas: list[FilaControlDiarioCartera]
