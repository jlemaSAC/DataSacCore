from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ConsultaCorteResultados(BaseModel):
    fecha_corte: date
    id_agencia: int = Field(default=0, ge=0, description="0 consulta el consolidado contable (agencia 1).")
    neteo: Literal[0, 1] = 1


class ConsultaRangoResultados(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    id_agencia: int = Field(default=0, ge=0, description="0 consulta el consolidado contable (agencia 1).")
    neteo: Literal[0, 1] = 1

    @model_validator(mode="after")
    def validar_rango(self):
        if self.fecha_desde > self.fecha_hasta:
            raise ValueError("fecha_desde no puede ser posterior a fecha_hasta.")
        return self


class ConsultaHistoricoResultados(ConsultaRangoResultados):
    @model_validator(mode="after")
    def validar_rango_diario(self):
        if (self.fecha_hasta - self.fecha_desde).days >= 366:
            raise ValueError("El rango no puede superar 366 días.")
        return self


class ConsultaHistoricoMensualResultados(ConsultaRangoResultados):
    @model_validator(mode="after")
    def validar_rango_mensual(self):
        meses = ((self.fecha_hasta.year - self.fecha_desde.year) * 12
                 + self.fecha_hasta.month - self.fecha_desde.month + 1)
        if meses > 48:
            raise ValueError("El rango mensual no puede superar 4 años (48 meses).")
        return self


class FilaResultadoEjercicio(BaseModel):
    codigo: str
    cuenta: str | None
    signo: Literal["", "+", "-"]
    nombre: str
    es_resultado: bool
    formula: str


class SaldoResultadoEjercicio(BaseModel):
    fecha: date
    codigo_fila: str
    saldo: Decimal | None


class ResultadosEjercicioResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    id_agencia: int
    id_agencia_contable: int
    nombre_agencia: str
    neteo: Literal[0, 1]
    fechas: list[date]
    filas: list[FilaResultadoEjercicio]
    datos: list[SaldoResultadoEjercicio]
    total_registros: int
