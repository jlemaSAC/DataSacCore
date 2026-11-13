from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class ConsultaBalanceResultados(BaseModel):
    fecha_corte: date
    id_agencia: int = Field(default=0, ge=0, description="0 consulta el consolidado contable (agencia 1).")
    neteo: Literal[0, 1] = 1


class IndicadorResultado(BaseModel):
    codigo: str
    nombre: str
    formula: str
    saldo: Decimal | None


class ValidacionUtilidad(BaseModel):
    estado: Literal["coincide", "diferencia", "sin_datos"]
    formula: str = "1 - 2 - 3"
    utilidad_sin_neteo: Decimal | None
    resultado_contable: Decimal | None
    diferencia: Decimal | None
    ajuste_neteo: Decimal | None
    cuentas_sin_saldo: list[str]


class ResumenBalanceResultados(BaseModel):
    fecha_corte: date
    id_agencia: int
    id_agencia_contable: int
    nombre_agencia: str
    neteo: Literal[0, 1]
    cuentas_sin_saldo: list[str]
    indicadores: list[IndicadorResultado]
    margenes: list[IndicadorResultado]
    validacion_utilidad: ValidacionUtilidad
