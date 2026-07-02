from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class InputRentabilidad(BaseModel):
    fecha_corte: datetime
    id_agencia: int = 1

    @field_validator("id_agencia")
    @classmethod
    def validar_id_agencia(cls, id_agencia: int) -> int:
        if id_agencia <= 0:
            raise ValueError("id_agencia debe ser mayor que 0.")
        return id_agencia


class RentabilidadResponse(BaseModel):
    fecha_corte: datetime
    fecha_promedio_desde: datetime
    id_agencia: int
    neteo: int
    mes: int
    indicadores: dict[str, float | None]
    saldos_cuentas: dict[str, float]
    saldos_promedio: dict[str, float]
    componentes: dict[str, float]


class InputRentabilidadHistorico(BaseModel):
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


class RentabilidadHistoricoItem(BaseModel):
    fecha_corte: date
    anio: int
    mes: int
    dia: int
    gasto_operacional_sobre_margen_financiero_neto: float | None
    roa: float | None
    roe: float | None
    gasto_operativo_estimado_sobre_cartera_bruta: float | None
    costo_promedio_fondeo: float | None


class RentabilidadHistoricoResponse(BaseModel):
    id_agencia: int
    periodo_desde: str
    periodo_hasta: str
    neteo: int
    datos: list[RentabilidadHistoricoItem]
    periodos_sin_datos: list[str]
