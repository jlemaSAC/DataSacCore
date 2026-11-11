from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ConsultaComparativaCuentas(BaseModel):
    mes_inicio: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Mes inicial inclusivo, YYYY-MM.")
    fecha_corte: date
    id_agencia: int = Field(default=0, ge=0, description="0 consulta el consolidado contable (agencia 1).")
    neteo: Literal[0, 1] = 1

    @model_validator(mode="after")
    def validar_intervalo(self):
        inicio = date.fromisoformat(f"{self.mes_inicio}-01")
        meses = (self.fecha_corte.year - inicio.year) * 12 + self.fecha_corte.month - inicio.month + 1
        if meses < 1:
            raise ValueError("El mes de inicio no puede ser posterior a la fecha de corte.")
        if meses > 24:
            raise ValueError("La comparación admite hasta 24 meses, incluido el mes de corte.")
        return self


class PeriodoComparativa(BaseModel):
    periodo: str
    fecha: date
    fecha_ajustada: bool
    cuentas_con_datos: int


class ValorComparativa(BaseModel):
    periodo: str
    saldo: Decimal | None
    variacion_absoluta: Decimal | None


class CuentaComparativa(BaseModel):
    codigo_cuenta: str
    nombre_cuenta: str
    codigo_padre: str | None
    nivel: int
    activa: bool
    es_movimiento: bool
    valores: list[ValorComparativa]


class ComparativaCuentasResponse(BaseModel):
    mes_inicio: str
    fecha_corte: date
    id_agencia: int
    id_agencia_contable: int
    nombre_agencia: str
    neteo: Literal[0, 1]
    total_cuentas: int
    periodos: list[PeriodoComparativa]
    cuentas: list[CuentaComparativa]
