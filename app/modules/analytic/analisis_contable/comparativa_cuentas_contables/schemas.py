from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ConsultaComparativaCuentas(BaseModel):
    mes_inicio: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Mes inicial inclusivo, YYYY-MM.")
    periodicidad: Literal["mensual", "anual", "diaria"] = "mensual"
    anio_inicio: int | None = Field(default=None, ge=1753, le=9999, description="Año inicial; SQL Server almacena los saldos con datetime desde 1753.")
    fecha_inicio: date | None = None
    fecha_corte: date
    id_agencia: int = Field(default=0, ge=0, description="0 consulta el consolidado contable (agencia 1).")
    neteo: Literal[0, 1] = 1

    @model_validator(mode="after")
    def validar_intervalo(self):
        if self.periodicidad == "diaria":
            if self.fecha_inicio is None or self.mes_inicio is not None or self.anio_inicio is not None:
                raise ValueError("La comparación diaria requiere fecha de inicio.")
            if self.fecha_inicio < date(1753, 1, 1) or self.fecha_inicio > self.fecha_corte:
                raise ValueError("La fecha de inicio debe ser válida y no posterior a la fecha de fin.")
            anio, mes_cero = divmod(self.fecha_inicio.year * 12 + self.fecha_inicio.month - 1 + 6, 12)
            if anio <= 9999:
                limite = date(anio, mes_cero + 1, min(self.fecha_inicio.day, monthrange(anio, mes_cero + 1)[1]))
                if self.fecha_corte > limite:
                    raise ValueError("La comparación diaria admite hasta seis meses calendario.")
            return self
        if self.fecha_inicio is not None:
            raise ValueError("La fecha de inicio solo corresponde a la comparación diaria.")
        if self.periodicidad == "anual":
            if self.anio_inicio is None or self.anio_inicio > self.fecha_corte.year:
                raise ValueError("El año de inicio debe ser válido y no posterior a la fecha de corte.")
            if self.mes_inicio is not None:
                raise ValueError("El mes de inicio solo corresponde a la comparación mensual.")
            return self
        if self.mes_inicio is None or self.anio_inicio is not None:
            raise ValueError("La comparación mensual requiere mes de inicio.")
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


class ConsultaComparativaAnualMeses(BaseModel):
    periodicidad: Literal["anual_meses"] = "anual_meses"
    anio_inicio: int = Field(ge=1754, le=9999)
    fecha_corte: date
    id_agencia: int = Field(default=0, ge=0)
    neteo: Literal[0, 1] = 1

    @model_validator(mode="after")
    def validar_intervalo(self):
        if self.anio_inicio > self.fecha_corte.year:
            raise ValueError("El año de inicio no puede ser posterior a la fecha de fin.")
        return self


class PeriodoComparativaAnualMeses(PeriodoComparativa):
    fecha_anterior: date
    fecha_anterior_ajustada: bool
    cuentas_con_datos_anterior: int


class ValorComparativaAnualMeses(ValorComparativa):
    saldo_anterior: Decimal | None


class CuentaComparativaAnualMeses(CuentaComparativa):
    valores: list[ValorComparativaAnualMeses]


class ComparativaAnualMesesResponse(ComparativaCuentasResponse):
    periodos: list[PeriodoComparativaAnualMeses]
    cuentas: list[CuentaComparativaAnualMeses]
