from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


FiltroTexto = str | list[str]
FiltroAgencia = str | list[str]


class MatrizTransicionRequest(BaseModel):
    """Cortes y filtros aplicables exclusivamente al corte nuevo."""

    fecha_corte_anterior: datetime = Field(description="Corte histórico para la comparación.")
    fecha_corte_nuevo: datetime = Field(description="Corte de comparación; usa la colección actual si es hoy.")
    agencia: FiltroAgencia | None = Field(
        default=None,
        alias="Agencia",
        description="Nombre o nombres de agencia; vacío consulta todas.",
    )
    diferido: bool | None = Field(default=None, alias="Diferido")
    cargo: FiltroTexto | None = Field(default=None, alias="Cargo")
    estado_prestamo: FiltroTexto | None = Field(default=None, alias="EstadoPrestamo")
    asesores: FiltroTexto | None = Field(default=None, alias="Asesores")

    model_config = ConfigDict(populate_by_name=True)


class MatrizTransicionPrestamosRequest(MatrizTransicionRequest):
    calificacion_anterior: str = Field(
        min_length=1,
        description="Calificación de origen; use NA para préstamos nuevos.",
    )
    calificacion_nueva: str = Field(min_length=1, description="Calificación de destino.")


class MatrizTransicionResponse(BaseModel):
    categorias: list[str]
    conteos: dict[str, dict[str, int]]
    probabilidades: dict[str, dict[str, float]]
    saldos_capital: dict[str, dict[str, dict[str, float]]]
    provision_requerida: dict[str, dict[str, dict[str, float]]]
    provision_constituida: dict[str, dict[str, dict[str, float]]]
    exigible_capital: dict[str, dict[str, dict[str, float]]]
    exigible_interes: dict[str, dict[str, dict[str, float]]]
    exigible_mora: dict[str, dict[str, dict[str, float]]]
    exigible_otros: dict[str, dict[str, dict[str, float]]]
    valor_para_estar_al_dia: dict[str, dict[str, dict[str, float]]]
    valor_hasta_cuota_actual: dict[str, dict[str, dict[str, float]]]
    valor_cancelar_total: dict[str, dict[str, dict[str, float]]]
    fecha_corte_anterior: str
    fecha_corte_nuevo: str
    fuente_corte_nuevo: str
