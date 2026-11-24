from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


TiempoInactividad = Literal[
    "0_1", "1_2", "2_3", "3_6", "6_12", "12_24", "24_36", "36_60",
    "mas_60", "mas_36", "sin_fecha"
]
FiltroSaldo = Literal["cero", "con_saldo"]


class ConsultaCuentasInactivas(BaseModel):
    id_agencia: int = Field(ge=0, description="0 consulta el consolidado de las agencias indicadas.")
    ids_agencia: list[Annotated[int, Field(gt=0)]] = Field(default_factory=list, max_length=2000)
    inactividad: TiempoInactividad | list[TiempoInactividad] | None = Field(
        default=None, description="Uno o varios rangos desde la última entrada al estado I."
    )
    saldo: FiltroSaldo | None = Field(
        default=None, description="Saldo total de la cuenta redondeado a centavos."
    )

    @model_validator(mode="after")
    def requerir_agencias_para_consolidado(self) -> "ConsultaCuentasInactivas":
        if self.id_agencia == 0 and not self.ids_agencia:
            raise ValueError("Indica las agencias que se incluirán en el consolidado.")
        return self


class DetalleCuentasInactivasRequest(ConsultaCuentasInactivas):
    cargos: list[Annotated[str, Field(min_length=1, max_length=150)]] = Field(default_factory=list, max_length=500)
    asesores: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(default_factory=list, max_length=2000)
    codigo_oficial: str | None = Field(default=None, max_length=100)
    codigo_tipo_cuenta: str | None = Field(default=None, max_length=50)
    pagina: int = Field(default=1, ge=1)
    tamano_pagina: int = Field(default=25, ge=1, le=100)
    sin_paginacion: bool = Field(default=False, description="Devuelve toda la selección en una consulta.")


class IndicadoresCuentas(BaseModel):
    cantidad_cuentas: int
    valor_disponible: Decimal
    valor_total: Decimal


class IndicadoresAgencia(IndicadoresCuentas):
    id_agencia: int
    agencia: str


class ResumenAgencia(IndicadoresAgencia):
    cargo_jefe_agencia: str | None = None
    nombre_jefe_agencia: str | None = None


class ResumenOficialTipoCuenta(IndicadoresAgencia):
    cargo: str
    codigo_oficial: str
    oficial: str
    codigo_tipo_cuenta: str
    tipo_cuenta: str


class ConsultaCuentasInactivasResponse(BaseModel):
    id_agencia: int
    fecha_sistema: date
    resumen: list[ResumenAgencia]
    desglose: list[ResumenOficialTipoCuenta]
    total: IndicadoresCuentas | None


class CuentaInactivaDetalle(BaseModel):
    numero_cuenta: str
    agencia: str
    titular: str | None
    oficial: str
    tipo_cuenta: str
    ultima_transaccion_activa: date | None
    fecha_inactivacion: date | None
    dias_inactividad: int | None
    valor_disponible: Decimal
    valor_total: Decimal


class DetalleCuentasInactivasResponse(BaseModel):
    fecha_sistema: date
    pagina: int | None
    tamano_pagina: int | None
    total_registros: int
    filas: list[CuentaInactivaDetalle]
