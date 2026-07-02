from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class InputIndicadoresDeLiquidez(BaseModel):
    fecha_corte: datetime
    id_agencia: int = 1

    @field_validator("id_agencia")
    @classmethod
    def validar_id_agencia(cls, id_agencia: int) -> int:
        if id_agencia <= 0:
            raise ValueError("id_agencia debe ser mayor que 0.")
        return id_agencia


class IndicadoresDeLiquidezResponse(BaseModel):
    fecha_corte: datetime
    id_agencia: int
    neteo: int
    indicadores: dict[str, float | None]
    saldos_cuentas: dict[str, float]
    componentes: dict[str, float]


class InputIndicadoresDeLiquidezHistorico(BaseModel):
    periodo_desde: str = Field(
        pattern=r"^[1-9]\d{3}-(0[1-9]|1[0-2])$",
        examples=["2025-01"],
    )
    periodo_hasta: str = Field(
        pattern=r"^[1-9]\d{3}-(0[1-9]|1[0-2])$",
        examples=["2026-05"],
    )
    id_agencia: int = 1

    @field_validator("id_agencia")
    @classmethod
    def validar_id_agencia(cls, id_agencia: int) -> int:
        if id_agencia <= 0:
            raise ValueError("id_agencia debe ser mayor que 0.")
        return id_agencia


class IndicadorDeLiquidezMensual(BaseModel):
    fecha_corte: date
    anio: int
    mes: int
    dia: int
    fondos_disponibles_sobre_depositos_corto_plazo: float | None
    liquidez_sobre_obligaciones_publico: float | None
    liquidez_inversiones_sobre_depositos_vista_plazo: float | None
    activos_liquidos_sobre_pasivos_exigibles: float | None
    inversiones_sobre_obligaciones_publico: float | None
    activos_liquidos_sobre_obligaciones_publico: float | None
    liquidez_primera_linea: float | None
    liquidez_segunda_linea: float | None


class IndicadoresDeLiquidezHistoricoResponse(BaseModel):
    id_agencia: int
    periodo_desde: str
    periodo_hasta: str
    neteo: int
    datos: list[IndicadorDeLiquidezMensual]
    periodos_sin_datos: list[str]
