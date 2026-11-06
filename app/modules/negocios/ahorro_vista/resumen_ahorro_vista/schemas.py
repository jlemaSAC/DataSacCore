from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InputResumenAhorroVista(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date
    fecha_fin: date
    agencias: list[str] = Field(default_factory=list)

    @field_validator("agencias")
    @classmethod
    def normalizar_agencias(cls, valores: list[str]) -> list[str]:
        if any(not valor.strip() for valor in valores):
            raise ValueError("agencias no puede contener nombres vacíos.")
        return list(dict.fromkeys(valor.strip().upper() for valor in valores))

    @model_validator(mode="after")
    def validar_rango(self) -> "InputResumenAhorroVista":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio.")
        if self.fecha_inicio.replace(day=1) != self.fecha_fin.replace(day=1):
            raise ValueError("fecha_inicio y fecha_fin deben pertenecer al mismo mes.")
        return self


class FilaResumenAhorroVista(BaseModel):
    agencia: str
    asesor: str
    estado: str
    producto_ahorro: str
    saldo: Decimal
    numero_cuentas: int = Field(ge=0)
    tasa_decimal: Decimal


class MetricasAhorroVista(BaseModel):
    saldo: float
    numero_cuentas: int = Field(ge=0)
    tasa_promedio: float | None


class IndicadoresAhorroVista(MetricasAhorroVista):
    fecha_corte: date


class AgenciaAhorroVista(MetricasAhorroVista):
    agencia: str


class AsesorAhorroVista(MetricasAhorroVista):
    asesor: str


class EstadoAhorroVista(MetricasAhorroVista):
    estado: str


class ProductoAhorroVista(MetricasAhorroVista):
    producto_ahorro: str


class SaldoDiarioAhorroVista(BaseModel):
    fecha: date
    saldo: float | None = Field(
        description="Saldo al corte del día; null si no existe cierre disponible."
    )


class ResumenAhorroVistaResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    fecha_mes_anterior: date
    fecha_anio_anterior: date
    consolidado: bool
    agencias: list[str]
    actual: IndicadoresAhorroVista | None
    mes_anterior: IndicadoresAhorroVista | None
    anio_anterior: IndicadoresAhorroVista | None
    por_agencia: list[AgenciaAhorroVista]
    por_asesor: list[AsesorAhorroVista]
    por_estado: list[EstadoAhorroVista]
    por_producto_ahorro: list[ProductoAhorroVista]
    saldo_diario: list[SaldoDiarioAhorroVista] = Field(
        description=(
            "Una entrada por fecha del rango, ordenada ascendentemente, con las mismas "
            "agencias y es_programado=false. Son saldos al corte, no flujos acumulados. "
            "El último día reutiliza el corte del indicador actual."
        )
    )
