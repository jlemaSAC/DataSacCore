from datetime import datetime

from pydantic import BaseModel, field_validator


class InputIndicadoresDeEficiencia(BaseModel):
    fecha_corte: datetime
    id_agencia: int = 1

    @field_validator("id_agencia")
    @classmethod
    def validar_id_agencia(cls, id_agencia: int) -> int:
        if id_agencia <= 0:
            raise ValueError("id_agencia debe ser mayor que 0.")
        return id_agencia


class IndicadoresDeEficienciaResponse(BaseModel):
    fecha_corte: datetime
    fecha_promedio_desde: datetime
    id_agencia: int
    neteo: int
    mes: int
    indicadores: dict[str, float | None]
    saldos_cuentas: dict[str, float]
    saldos_promedio: dict[str, float]
    componentes: dict[str, float]
