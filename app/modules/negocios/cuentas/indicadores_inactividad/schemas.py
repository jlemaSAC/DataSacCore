from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from ..schemas import AgenciasConsulta


CondicionSaldo = Literal["todas", "cero", "positivo"]
DimensionInactividad = Literal[
    "rango_edad", "sexo", "estado_civil", "socio", "agencia", "anio", "mes_agencia", "mes_apertura",
]


class IndicadoresInactividadRequest(AgenciasConsulta):
    condicion_saldo: CondicionSaldo = "todas"


class IndicadoresGenerales(BaseModel):
    cuentas_brutas: int
    cuentas_cero: int
    cuentas_positivas: int
    cuentas_seleccionadas: int
    porcentaje_base_bruta: float | None
    porcentaje_con_saldo: float | None
    saldo_total: Decimal
    saldo_socios: Decimal
    saldo_no_socios: Decimal
    saldo_socio_no_especificado: Decimal
    saldo_maximo: Decimal | None
    saldo_minimo: Decimal | None
    saldo_restante: Decimal


class Estadisticas(BaseModel):
    cuentas_con_dato: int
    promedio: float | None
    maximo: int | None
    minimo: int | None
    rango: int | None


class GrupoInactividad(BaseModel):
    clave: str
    nombre: str
    id_agencia: int | None = None
    agencia: str | None = None
    cantidad: int
    porcentaje: float


class IndicadoresInactividadResponse(BaseModel):
    id_agencia: int
    fecha_corte: date
    condicion_saldo: CondicionSaldo
    generales: IndicadoresGenerales
    inactividad: Estadisticas | None
    ultima_transaccion_activa: Estadisticas | None
    dimensiones: dict[DimensionInactividad, list[GrupoInactividad]]
