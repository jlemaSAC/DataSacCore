from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class InputCalidadDeActivos(BaseModel):
    fecha_corte: datetime
    id_agencia: int = 1

    @field_validator("id_agencia")
    @classmethod
    def validar_id_agencia(cls, id_agencia: int) -> int:
        if id_agencia <= 0:
            raise ValueError("id_agencia debe ser mayor que 0.")
        return id_agencia


class CalidadDeActivosResponse(BaseModel):
    fecha_corte: datetime
    id_agencia: int
    neteo: int
    indicadores: dict[str, float | None]
    saldos_cuentas: dict[str, float]
    componentes: dict[str, float]


class InputCalidadDeActivosHistorico(BaseModel):
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


class CalidadDeActivosHistoricoItem(BaseModel):
    fecha_corte: date
    anio: int
    mes: int
    dia: int
    morosidad_ampliada: float | None
    morosidad_consumo: float | None
    morosidad_inmobiliaria: float | None
    morosidad_micro: float | None
    activos_improductivos_netos_sobre_activo: float | None
    cartera_refinanciada_restructurada_sobre_cartera_total: float | None
    cartera_bruta_sobre_activos: float | None
    cobertura_cartera_en_riesgo: float | None


class CalidadDeActivosHistoricoResponse(BaseModel):
    id_agencia: int
    periodo_desde: str
    periodo_hasta: str
    neteo: int
    datos: list[CalidadDeActivosHistoricoItem]
    periodos_sin_datos: list[str]
