from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from ..schemas import AgenciasConsulta


class ConsultaCuentasReactivadas(AgenciasConsulta):
    fecha_inicio: date
    fecha_fin: date

    @model_validator(mode="after")
    def validar_rango(self) -> "ConsultaCuentasReactivadas":
        if self.fecha_inicio > self.fecha_fin:
            raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
        if self.fecha_inicio.replace(day=1) != self.fecha_fin.replace(day=1):
            raise ValueError("El rango de consulta debe pertenecer al mismo mes.")
        return self


class DetalleCuentasReactivadasRequest(ConsultaCuentasReactivadas):
    codigo_tipo_cuenta: str | None = Field(default=None, min_length=1, max_length=50)
    cargos: list[Annotated[str, Field(min_length=1, max_length=150)]] = Field(default_factory=list, max_length=500)
    asesores: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(default_factory=list, max_length=2000)
    desplazamiento: int = Field(default=0, ge=0, le=2_147_483_647)
    tamano_pagina: int = Field(default=25, ge=1, le=100)
    sin_paginacion: bool = False


class IndicadoresReactivaciones(BaseModel):
    cantidad_cuentas: int
    cantidad_reactivaciones: int
    total_recaudado: Decimal | None = None


class ResumenReactivaciones(IndicadoresReactivaciones):
    id_agencia: int
    agencia: str
    codigo_tipo_cuenta: str
    tipo_cuenta: str
    cargo_jefe_agencia: str | None = None
    nombre_jefe_agencia: str | None = None


class DesgloseReactivaciones(ResumenReactivaciones):
    cargo: str
    codigo_asesor: str
    asesor: str


class ConsultaCuentasReactivadasResponse(BaseModel):
    resumen: list[ResumenReactivaciones]
    desglose: list[DesgloseReactivaciones]
    total: IndicadoresReactivaciones


class ReactivacionDetalle(BaseModel):
    id_reactivacion: int
    fecha_reactivacion: date
    numero_cuenta: str
    titular: str | None
    tipo_cuenta: str
    agencia: str
    asesor: str
    cargo: str
    transaccion: str | None
    valor_transaccion: Decimal | None


class DetalleCuentasReactivadasResponse(BaseModel):
    filas: list[ReactivacionDetalle]
