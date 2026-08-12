from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ReporteInversionesFila(BaseModel):
    fecha_corte: str
    periodo: str
    anio: int
    mes: int
    agencia: str
    asesor: str
    periodicidad_pago: str
    tipo_pago: str
    condicion: str
    periodo_plazo: str
    plazo_dias: int | None = None
    estado: str
    provincia: str
    canton: str
    parroquia: str
    tiene_prestamo: bool
    tasa_efectiva: float
    tasa_entera: int
    tasa_decimal: float
    operaciones: int
    saldo: float

    @field_validator("fecha_corte", mode="before")
    @classmethod
    def normalizar_fecha_corte(cls, value: Any) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y%m%d")
        if isinstance(value, date):
            return value.strftime("%Y%m%d")
        return str(value)


class CorteInversionesResponse(BaseModel):
    periodo: str = Field(description="Mes consultado en formato YYYY-MM.")
    fecha_corte: str | None = Field(
        default=None,
        description="Corte real obtenido; puede ser el último día operativo del mes.",
    )
    origen: Literal["MONGO", "ETL_EN_DEMANDA", "SQL_EN_LINEA", "SIN_CORTE_DISPONIBLE"]
    total_filas: int = Field(ge=0)
    operaciones: int = Field(ge=0)
    saldo: float


class ReporteInversionesRangoResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    total_operaciones: int = Field(ge=0)
    total_saldo: float
    cortes: list[CorteInversionesResponse]
    filas: list[ReporteInversionesFila]
