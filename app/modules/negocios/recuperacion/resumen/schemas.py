from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InputResumenRecuperacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agencias: list[str] = Field(min_length=1, examples=[["MATRIZ", "CUENCA"]])
    fecha_inicio: date = Field(examples=["2026-08-01"])
    fecha_fin: date = Field(examples=["2026-08-31"])
    asesores: list[str] = Field(default_factory=list, examples=[["JUAN PEREZ"]])
    cargos: list[str] = Field(default_factory=list, examples=[["GESTOR DE COBRANZAS"]])

    @field_validator("agencias", "asesores", "cargos", mode="after")
    @classmethod
    def normalizar_listas(cls, valores: list[str]) -> list[str]:
        normalizados: list[str] = []
        vistos: set[str] = set()
        for valor in valores:
            texto = valor.strip().upper()
            if not texto:
                raise ValueError("Los filtros no pueden contener valores vacíos.")
            if texto not in vistos:
                vistos.add(texto)
                normalizados.append(texto)
        return normalizados

    @model_validator(mode="after")
    def validar_rango(self) -> "InputResumenRecuperacion":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio.")
        if (self.fecha_inicio.year, self.fecha_inicio.month) != (
            self.fecha_fin.year,
            self.fecha_fin.month,
        ):
            raise ValueError("El rango de consulta debe estar dentro del mismo mes.")
        return self


class FilaAgrupacionRecuperacion(BaseModel):
    agencia: str | None = None
    dimension: str
    numero_operaciones: int
    numero_operaciones_periodo_anterior: int
    numero_operaciones_mismo_rango_mes_anterior: int
    variacion_operaciones: int
    monto_recuperado: float
    monto_recuperado_periodo_anterior: float
    monto_mismo_rango_mes_anterior: float
    variacion_valor: float


class AgrupacionesResumenRecuperacion(BaseModel):
    por_agencia: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_asesor: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_cargo: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_tipo_prestamo: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_producto: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_condicion: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_tipo_cobro: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_abogado: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)


class ResumenRecuperacionResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    fecha_inicio_periodo_anterior: date
    fecha_fin_periodo_anterior: date
    fecha_inicio_mismo_rango_mes_anterior: date
    fecha_fin_mismo_rango_mes_anterior: date
    asesores_disponibles: list[str]
    cargos_disponibles: list[str]
    agrupaciones: AgrupacionesResumenRecuperacion
