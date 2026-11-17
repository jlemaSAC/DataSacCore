from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, model_validator
from app.modules.contabilidad.saldos_diarios.service import fecha_actual_ecuador


class ConsultaVariacion(BaseModel):
    tipo: Literal['anual', 'mensual', 'mensual_cortes', 'anual_meses']
    fecha_desde: date
    fecha_hasta: date
    id_agencia: int = Field(default=0, ge=0)
    neteo: Literal[0, 1] = 1
    dia_mes: int | None = Field(default=None, ge=1, le=31)

    @model_validator(mode='after')
    def validar_rango(self):
        if self.tipo != 'anual' and self.dia_mes is not None:
            raise ValueError('El día del mes solo se admite para la variación anual.')
        if self.fecha_desde > self.fecha_hasta or self.fecha_hasta > fecha_actual_ecuador():
            raise ValueError('Rango de fechas inválido o futuro.')
        meses = 12 if self.tipo == 'mensual' else 48
        indice = self.fecha_desde.year * 12 + self.fecha_desde.month - 1 + meses
        anio, mes = divmod(indice, 12)
        if anio > 9999:
            return self
        limite = date(anio, mes + 1, min(self.fecha_desde.day, monthrange(anio, mes + 1)[1]))
        if self.fecha_hasta >= limite:
            raise ValueError(f'El rango máximo es de {meses} meses.')
        if self.fecha_desde < date(1754, 1, 1):
            raise ValueError('Fecha inicial fuera del rango permitido.')
        return self


class CorteVariacion(BaseModel):
    fecha: date
    fecha_comparacion: date
    activos: Decimal | None
    pasivos: Decimal | None
    patrimonio: Decimal | None
    cuentas_sin_saldo: list[str]


class VariacionResponse(ConsultaVariacion):
    id_agencia_contable: int
    nombre_agencia: str
    datos: list[CorteVariacion]
