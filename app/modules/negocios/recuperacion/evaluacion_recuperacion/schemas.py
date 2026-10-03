from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InputEvaluacionRecuperacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agencias: list[str] = Field(min_length=1, examples=[["MATRIZ", "CUENCA"]])
    fecha_inicio: date = Field(examples=["2026-08-01"])
    fecha_fin: date = Field(examples=["2026-08-31"])
    incluir_cubos_filtro: bool = Field(
        default=False,
        description=(
            "Incluye los cubos para el filtrado local por asesor y cargo. "
            "Debe solicitarse solo después de aplicar esos filtros."
        ),
    )

    @field_validator("agencias", mode="after")
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
    def validar_rango(self) -> "InputEvaluacionRecuperacion":
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


class AgrupacionesEvaluacionRecuperacion(BaseModel):
    por_agencia: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_asesor: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_cargo: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_tipo_prestamo: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_producto: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_condicion: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_tipo_cobro: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)
    por_abogado: list[FilaAgrupacionRecuperacion] = Field(default_factory=list)


class CuboFiltroRecuperacion(BaseModel):
    periodo: str
    tipo_dimension: str
    dimension: str
    agencia: str | None = None
    asesor: str
    cargo: str
    numero_operaciones: int
    monto_recuperado: float


class DesgloseCobroRecuperacion(BaseModel):
    tipo_dimension: str
    dimension: str
    agencia: str | None = None
    asesor: str
    cargo: str
    tipo_cobro: str
    numero_rubros: int
    monto_recuperado: float


class EvaluacionRecuperacionResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    fecha_inicio_periodo_anterior: date
    fecha_fin_periodo_anterior: date
    fecha_inicio_mismo_rango_mes_anterior: date
    fecha_fin_mismo_rango_mes_anterior: date
    asesores_disponibles: list[str]
    cargos_disponibles: list[str]
    cubos_filtro: list[CuboFiltroRecuperacion]
    desglose_cobros: list[DesgloseCobroRecuperacion]
    agrupaciones: AgrupacionesEvaluacionRecuperacion


DimensionDetalleRecuperacion = Literal[
    "agencia",
    "asesor",
    "cargo",
    "tipo_prestamo",
    "producto",
    "condicion",
    "tipo_cobro",
    "abogado",
]


class InputDetalleEvaluacionRecuperacion(InputEvaluacionRecuperacion):
    dimension: DimensionDetalleRecuperacion
    valor_dimension: str = Field(min_length=1, examples=["MATRIZ"])
    asesores: list[str] = Field(default_factory=list)
    cargos: list[str] = Field(default_factory=list)
    pagina: int = Field(default=1, ge=1)
    tamano_pagina: int = Field(default=100, ge=1, le=200)

    @field_validator("valor_dimension", mode="after")
    @classmethod
    def normalizar_dimension(cls, valor: str) -> str:
        texto = valor.strip().upper()
        if not texto:
            raise ValueError("valor_dimension no puede estar vacío.")
        return texto

    @field_validator("asesores", "cargos", mode="after")
    @classmethod
    def normalizar_filtros_locales(cls, valores: list[str]) -> list[str]:
        return InputEvaluacionRecuperacion.normalizar_listas(valores)


class FilaDetalleRecuperacion(BaseModel):
    socio: int | None = None
    numero_prestamo: str
    nombre: str
    estado_prestamo: str
    calificacion_actual: str
    fecha_ultimo_cobro: date
    saldo_capital: float
    total_recuperado_mes: float
    pendiente_pago: float
    valor_al_dia_mas_cuota_actual: float
    cuotas_pagadas: int
    total_cuotas: int
    es_diferido: bool


class TotalesPaginaDetalleRecuperacion(BaseModel):
    saldo_capital: float
    total_recuperado_mes: float
    pendiente_pago: float
    valor_al_dia_mas_cuota_actual: float
    cuotas_pagadas: int
    total_cuotas: int


class DetalleEvaluacionRecuperacionResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    dimension: DimensionDetalleRecuperacion
    valor_dimension: str
    pagina: int
    tamano_pagina: int
    total_registros: int
    total_paginas: int
    total_recuperado_mes: float
    totales_pagina: TotalesPaginaDetalleRecuperacion
    items: list[FilaDetalleRecuperacion]
