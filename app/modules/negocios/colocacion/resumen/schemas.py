from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.prestamos.normalizadores import normalizar_texto


class InputResumenColocacion(BaseModel):
    agencias: list[str] = Field(min_length=1, examples=[["MATRIZ", "CUENCA"]])
    fecha_inicio: date = Field(examples=["2026-08-01"])
    fecha_fin: date = Field(examples=["2026-08-31"])

    @model_validator(mode="after")
    def validar_rango(self) -> "InputResumenColocacion":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio.")
        if (self.fecha_inicio.year, self.fecha_inicio.month) != (self.fecha_fin.year, self.fecha_fin.month):
            raise ValueError("El rango de consulta debe estar dentro del mismo mes.")
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
    tasa_real: float | None
    numero_operaciones: int
    numero_operaciones_periodo_anterior: int
    numero_operaciones_mismo_rango_mes_anterior: int
    variacion_operaciones: int
    monto_colocado: float
    monto_colocado_periodo_anterior: float
    monto_mismo_rango_mes_anterior: float
    variacion_valor: float


class FilaAgrupacionColocacion(BaseModel):
    agencia: str | None = None
    dimension: str
    tasa_desde: float | None = None
    tasa_hasta_exclusiva: float | None = None
    numero_operaciones: int
    numero_operaciones_periodo_anterior: int
    numero_operaciones_mismo_rango_mes_anterior: int
    variacion_operaciones: int
    monto_colocado: float
    monto_colocado_periodo_anterior: float
    monto_mismo_rango_mes_anterior: float
    variacion_valor: float


class AgrupacionesResumenColocacion(BaseModel):
    por_agencia: list[FilaAgrupacionColocacion] = Field(default_factory=list)
    por_asesor: list[FilaAgrupacionColocacion] = Field(default_factory=list)
    por_tipo_prestamo: list[FilaAgrupacionColocacion] = Field(default_factory=list)
    por_producto: list[FilaAgrupacionColocacion] = Field(default_factory=list)
    por_segmento: list[FilaAgrupacionColocacion] = Field(default_factory=list)
    por_condicion: list[FilaAgrupacionColocacion] = Field(default_factory=list)
    por_tasa_normal: list[FilaAgrupacionColocacion] = Field(default_factory=list)
    por_tasa_real: list[FilaAgrupacionColocacion] = Field(default_factory=list)


class ResumenColocacionResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    fecha_inicio_periodo_anterior: date
    fecha_fin_periodo_anterior: date
    fecha_inicio_mismo_rango_mes_anterior: date
    fecha_fin_mismo_rango_mes_anterior: date
    asesores_disponibles: list[str]
    filas_filtro: list[FilaComparativaColocacion]
    agrupaciones: AgrupacionesResumenColocacion


class InputResumenActualColocacion(BaseModel):
    """Filtro del comparativo por rango; sin agencias representa el consolidado."""

    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date = Field(description="Primera fecha incluida.")
    fecha_fin: date = Field(description="Última fecha incluida.")
    agencias: list[str] = Field(
        default_factory=list,
        description="Agencias por nombre. Una lista vacía consulta el consolidado.",
    )

    @field_validator("agencias")
    @classmethod
    def normalizar_agencias(cls, valores: list[str]) -> list[str]:
        return list(
            dict.fromkeys(
                agencia
                for valor in valores
                if (agencia := normalizar_texto(valor))
            )
        )

    @model_validator(mode="after")
    def validar_rango(self) -> "InputResumenActualColocacion":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio.")
        if (self.fecha_inicio.year, self.fecha_inicio.month) != (
            self.fecha_fin.year,
            self.fecha_fin.month,
        ):
            raise ValueError("fecha_inicio y fecha_fin deben pertenecer al mismo mes.")
        return self


class RangoResumenActualColocacion(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    colocacion_general: float = Field(
        description="Suma de DeudaInicial de las operaciones adjudicadas en el rango."
    )
    monto_promedio: float = Field(
        description="Monto promedio colocado por operación en el rango."
    )
    tasa_promedio_colocacion: float | None = Field(
        description="Promedio simple de TasaNominal por operación con tasa válida."
    )
    tasa_real_promedio_colocacion: float | None = Field(
        description="Promedio simple de TasaAnual/TEA por operación con tasa válida."
    )
    numero_operaciones: int


class ColocacionPorAgencia(BaseModel):
    agencia: str
    monto_colocado: float = Field(
        description="Suma de DeudaInicial de la agencia en el rango seleccionado."
    )
    numero_operaciones: int = Field(
        description="Número de operaciones de la agencia en el rango seleccionado."
    )
    monto_promedio: float = Field(
        description="Monto promedio colocado por operación de la agencia."
    )


class ResumenActualColocacionResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    consolidado: bool
    agencias: list[str]
    colocacion_por_agencia: list[ColocacionPorAgencia] = Field(
        description="Montos de todas las agencias del rango seleccionado, sin aplicar el filtro de agencias."
    )
    acumulado_anual: RangoResumenActualColocacion = Field(
        description="Colocación acumulada desde el 1 de enero hasta la fecha fin seleccionada."
    )
    actual: RangoResumenActualColocacion
    mes_anterior: RangoResumenActualColocacion
    anio_anterior: RangoResumenActualColocacion


DimensionDetalleColocacion = Literal[
    "agencia",
    "asesor",
    "tipo_prestamo",
    "producto",
    "segmento",
    "condicion",
    "tasa_normal",
    "tasa_real",
]


class InputDetalleResumenColocacion(BaseModel):
    agencias: list[str] = Field(min_length=1, examples=[["QUITO"]])
    fecha_inicio: date = Field(examples=["2026-08-01"])
    fecha_fin: date = Field(examples=["2026-08-31"])
    dimension: DimensionDetalleColocacion
    valor_dimension: str = Field(min_length=1, examples=["CREDI AGIL CONSUMO"])
    tasa_desde: float | None = Field(default=None, ge=0, examples=[4])
    tasa_hasta_exclusiva: float | None = Field(default=None, gt=0, examples=[5])
    asesores: list[str] = Field(default_factory=list)
    pagina: int = Field(default=1, ge=1)
    tamano_pagina: int = Field(default=100, ge=1, le=500)

    @model_validator(mode="after")
    def validar_filtros(self) -> "InputDetalleResumenColocacion":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio.")
        if (self.fecha_inicio.year, self.fecha_inicio.month) != (self.fecha_fin.year, self.fecha_fin.month):
            raise ValueError("El rango de consulta debe estar dentro del mismo mes.")
        if any(not agencia.strip() for agencia in self.agencias):
            raise ValueError("agencias no puede contener nombres vacíos.")
        if not self.valor_dimension.strip():
            raise ValueError("valor_dimension no puede estar vacío.")
        tiene_rango_tasa_real = self.tasa_desde is not None or self.tasa_hasta_exclusiva is not None
        if tiene_rango_tasa_real:
            if self.dimension != "tasa_real":
                raise ValueError("El rango de tasa solo aplica para la dimensión tasa_real.")
            if self.tasa_desde is None or self.tasa_hasta_exclusiva is None:
                raise ValueError("tasa_desde y tasa_hasta_exclusiva son requeridas para el rango de tasa real.")
            if self.tasa_hasta_exclusiva <= self.tasa_desde:
                raise ValueError("tasa_hasta_exclusiva debe ser mayor que tasa_desde.")
        if (
            self.dimension in {"tasa_normal", "tasa_real"}
            and not tiene_rango_tasa_real
            and self.valor_dimension.strip().upper() != "SIN DATOS"
        ):
            try:
                valor_tasa = float(self.valor_dimension)
            except ValueError as exc:
                raise ValueError("valor_dimension debe ser numérico para una tasa.") from exc
            if valor_tasa < 0:
                raise ValueError("valor_dimension no puede ser negativo para una tasa.")
        if any(not asesor.strip() for asesor in self.asesores):
            raise ValueError("asesores no puede contener nombres vacíos.")
        return self


class FilaDetalleColocacion(BaseModel):
    numero_cliente: str
    nombre_cliente: str
    numero_operacion: str
    agencia: str
    asesor: str
    tipo_condicion: str
    producto: str
    tipo_prestamo: str
    segmento: str
    tasa_nominal: float | None
    tasa_real: float | None
    monto_colocado: float


class DetalleResumenColocacionResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    dimension: DimensionDetalleColocacion
    valor_dimension: str
    pagina: int
    tamano_pagina: int
    total_registros: int
    total_monto_colocado: float
    items: list[FilaDetalleColocacion]
