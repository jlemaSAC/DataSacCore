from calendar import monthrange
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.contabilidad.saldos_diarios.service import fecha_actual_ecuador


class ConsultaEvolucionBalance(BaseModel):
    frecuencia: Literal["mensual", "diario"] = "mensual"
    fecha_desde: date
    fecha_hasta: date
    id_agencia: int = Field(default=0, ge=0, description="0 corresponde al consolidado contable (agencia 1).")
    neteo: Literal[0, 1] = 1

    @model_validator(mode="after")
    def validar_rango(self):
        if self.fecha_desde > self.fecha_hasta:
            raise ValueError("La fecha inicial no puede ser posterior a la final.")
        hoy = fecha_actual_ecuador()
        if self.fecha_hasta > hoy:
            raise ValueError("El rango no puede incluir fechas futuras.")
        meses = (self.fecha_hasta.year - self.fecha_desde.year) * 12 + self.fecha_hasta.month - self.fecha_desde.month
        if self.frecuencia == "mensual":
            if meses >= 48:
                raise ValueError("El histórico mensual admite como máximo 48 meses (4 años).")
        else:
            indice = self.fecha_desde.year * 12 + self.fecha_desde.month - 1 + 6
            anio, mes = divmod(indice, 12)
            limite = date(anio, mes + 1, min(self.fecha_desde.day, monthrange(anio, mes + 1)[1]))
            if self.fecha_hasta >= limite:
                raise ValueError("El histórico diario admite como máximo 6 meses, con límite final exclusivo.")
        return self


class CorteBalance(BaseModel):
    fecha: date
    parcial: bool = False
    activos: Decimal | None
    pasivos: Decimal | None
    patrimonio: Decimal | None
    cuentas_sin_saldo: list[str]


class EvolucionBalanceResponse(BaseModel):
    frecuencia: Literal["mensual", "diario"]
    fecha_desde: date
    fecha_hasta: date
    id_agencia: int
    neteo: Literal[0, 1]
    id_agencia_contable: int
    nombre_agencia: str
    datos: list[CorteBalance]
