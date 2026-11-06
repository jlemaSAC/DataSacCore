from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DepositosYRetirosDiariosRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date = Field(ge=date(1900, 1, 1), le=date(9998, 12, 31))
    fecha_fin: date = Field(ge=date(1900, 1, 1), le=date(9998, 12, 31))
    id_agencia: int = Field(default=0, ge=0, description="0 para consolidado.")

    @model_validator(mode="after")
    def validar_rango(self) -> "DepositosYRetirosDiariosRequest":
        if self.fecha_inicio > self.fecha_fin:
            raise ValueError("fecha_inicio no puede ser posterior a fecha_fin.")
        if self.fecha_inicio.replace(day=1) != self.fecha_fin.replace(day=1):
            raise ValueError("fecha_inicio y fecha_fin deben pertenecer al mismo mes.")
        return self


class TransaccionAhorroVistaDia(BaseModel):
    id_transaccion: int = Field(description="ID del tipo en FINANCIERO.TRANSACCION, no de una operación individual.")
    tipo_transaccion: str
    valor: float = Field(gt=0, description="Importe positivo agrupado por tipo y sentido dentro del día.")
    es_debito: bool = Field(description="true: salida de la cuenta; false: crédito o entrada.")


class DepositosYRetirosDia(BaseModel):
    depositos: float = Field(default=0, ge=0, description="Suma de variaciones positivas por operación y cuenta.")
    retiros: float = Field(default=0, ge=0, description="Magnitud de las variaciones negativas por operación y cuenta.")
    transacciones: list[TransaccionAhorroVistaDia] = Field(default_factory=list)


class DepositosYRetirosDiariosFila(BaseModel):
    codigo_usuario: str
    nombre_asesor: str
    id_agencia: int
    agencia: str
    codigo_producto: str = Field(description="Código de AHORROS.TIPO_CUENTA.")
    producto_ahorro: str
    valores: list[DepositosYRetirosDia] = Field(
        description="Totales y desglose por tipo y sentido para cada fecha, en el mismo orden de dias."
    )


class DepositosYRetirosDiariosResponse(DepositosYRetirosDiariosRequest):
    fecha_corte: date
    dias: list[date]
    filas: list[DepositosYRetirosDiariosFila]
