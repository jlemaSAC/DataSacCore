from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ConsultaSaldosDiarios(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    id_agencia: int = Field(ge=0, description="0 consulta el consolidado contable (agencia 1).")
    neteo: Literal[0, 1] = 1

    @model_validator(mode="after")
    def validar_rango(self):
        if self.fecha_desde > self.fecha_hasta:
            raise ValueError("fecha_desde no puede ser posterior a fecha_hasta.")
        if (self.fecha_hasta - self.fecha_desde).days >= 366:
            raise ValueError("El rango no puede superar 366 días.")
        return self


class SaldoDiario(BaseModel):
    fecha: date
    codigo_cuenta: str
    nombre_cuenta: str
    saldo: Decimal


class SaldosDiariosResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    id_agencia: int
    id_agencia_contable: int
    neteo: Literal[0, 1]
    total_registros: int
    datos: list[SaldoDiario]
