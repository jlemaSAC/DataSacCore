from pydantic import BaseModel, Field


class InputSaldoInicialAgencia(BaseModel):
    anio: int = Field(ge=1900)


class SaldoInicialMes(BaseModel):
    mes: int
    saldo_inicial: float


class SaldoInicialAgenciaDetalle(BaseModel):
    agencia: str
    meses: list[SaldoInicialMes]


class SaldoInicialAgenciaResponse(BaseModel):
    anio: int
    agencias: list[SaldoInicialAgenciaDetalle]
