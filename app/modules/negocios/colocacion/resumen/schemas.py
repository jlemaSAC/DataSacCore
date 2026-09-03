from datetime import date

from pydantic import BaseModel, Field, model_validator


class InputResumenColocacion(BaseModel):
    agencia_ids: list[int] = Field(
        min_length=1,
        examples=[[2, 17]],
        description="Identificadores de las agencias que se desean consultar.",
    )
    fecha_inicio: date = Field(examples=["2026-08-01"])
    fecha_fin: date = Field(examples=["2026-08-31"])

    @model_validator(mode="after")
    def validar_rango(self) -> "InputResumenColocacion":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio.")
        return self


class FilaResumenColocacion(BaseModel):
    id_agencia: int
    agencia: str
    dimension: str | None = Field(
        default=None,
        description="Valor del desglose; es nulo en el resumen por agencia.",
    )
    monto_colocado: float
    monto_colocado_periodo_anterior: float
    variacion_valor: float
    variacion_porcentaje: float | None
    monto_mes_a_fecha: float
    monto_mes_anterior_mismo_dia: float
    variacion_mes_a_fecha_valor: float
    variacion_mes_a_fecha_porcentaje: float | None


class ResumenColocacionResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    fecha_inicio_periodo_anterior: date
    fecha_fin_periodo_anterior: date
    fecha_inicio_mes_a_fecha: date
    fecha_fin_mes_a_fecha: date
    fecha_inicio_mes_anterior_mismo_dia: date
    fecha_fin_mes_anterior_mismo_dia: date
    resumen_por_agencia: list[FilaResumenColocacion]
    por_tipo_prestamo: list[FilaResumenColocacion]
    por_producto: list[FilaResumenColocacion]
    por_segmento: list[FilaResumenColocacion]
    por_condicion: list[FilaResumenColocacion]
