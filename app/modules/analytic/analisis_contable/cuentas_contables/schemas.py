from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class ConsultaCuentasContables(BaseModel):
    fecha_corte: date
    id_agencia: int = Field(default=0, ge=0, description="0 consulta el consolidado contable (agencia 1).")
    neteo: Literal[0, 1] = 1


class IndicadorContable(BaseModel):
    codigo: str
    nombre: str
    formula: str
    saldo: Decimal | None


class ResumenCuentasContables(BaseModel):
    fecha_corte: date
    id_agencia: int
    id_agencia_contable: int
    nombre_agencia: str
    neteo: Literal[0, 1]
    cuentas_sin_saldo: list[str]
    indicadores: list[IndicadorContable]
