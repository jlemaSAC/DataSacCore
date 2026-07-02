from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class InputSolvencia(BaseModel):
    fecha_corte: datetime
    id_agencia: int = 1
    deficiencia: float | None = Field(
        default=None,
        description="Deficiencia de provision a restar del patrimonio tecnico secundario.",
    )

    @field_validator("id_agencia")
    @classmethod
    def validar_id_agencia(cls, id_agencia: int) -> int:
        if id_agencia <= 0:
            raise ValueError("id_agencia debe ser mayor que 0.")
        return id_agencia


class SolvenciaResponse(BaseModel):
    fecha_corte: datetime
    id_agencia: int
    neteo: int
    mes: int
    deficiencia: float
    deficiencia_fuente: str
    provision_requerida: float
    provision_constituida: float
    utilidad: float
    patrimonio_tecnico_primario: float
    patrimonio_tecnico_secundario: float
    patrimonio_tecnico_constituido: float
    activos_improductivos_netos: float
    activos_ponderados_por_riesgo: float
    indicadores: dict[str, float | None]
    saldos_cuentas: dict[str, float]
    componentes: dict[str, float]


class InputSolvenciaHistorico(BaseModel):
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


class SolvenciaHistoricoItem(BaseModel):
    fecha_corte: date
    anio: int
    mes: int
    dia: int
    solvencia: float | None
    activos_fijos_sobre_patrimonio_tecnico: float | None
    patrimonio_sobre_activo: float | None
    patrimonio_resultados_sobre_activos_improductivos_netos: float | None


class SolvenciaHistoricoResponse(BaseModel):
    id_agencia: int
    periodo_desde: str
    periodo_hasta: str
    neteo: int
    datos: list[SolvenciaHistoricoItem]
    periodos_sin_datos: list[str]
