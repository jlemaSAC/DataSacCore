from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ReporteAhorroVistaFila(BaseModel):
    fecha_corte: str
    periodo: str
    anio: int
    mes: int
    agencia: str
    asesor: str
    periodicidad: int | None = Field(
        description="Días desde la última transacción al corte; coincide temporalmente con tiempo_inactivo_dias."
    )
    numero_transacciones_mes: int = Field(ge=0)
    numero_debitos_mes: int = Field(ge=0)
    numero_creditos_mes: int = Field(ge=0)
    tasa_entera: int
    tasa_decimal: float
    tiempo_inactivo_dias: int | None
    estado: str
    provincia: str
    canton: str
    parroquia: str
    tiene_prestamo: bool
    cantidad_prestamos: int
    tipo_prestamo: list[str] = Field(default_factory=list)
    producto: list[str] = Field(
        default_factory=list,
        description="Productos de préstamos vigentes del titular al corte.",
    )
    producto_ahorro: str
    es_programado: bool
    saldo: float

    @model_validator(mode="before")
    @classmethod
    def normalizar_listas_de_prestamos(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        fila = dict(value)
        for campo, campo_origen in (
            ("tipo_prestamo", "tipo_prestamo_lista"),
            ("producto", "producto_lista"),
        ):
            if campo in fila or campo_origen not in fila:
                continue
            valor = fila[campo_origen]
            fila[campo] = (
                [elemento.strip() for elemento in str(valor).split("\u200b") if elemento.strip()]
                if valor
                else []
            )
        return fila

    @field_validator("fecha_corte", mode="before")
    @classmethod
    def normalizar_fecha_corte(cls, value: Any) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y%m%d")
        if isinstance(value, date):
            return value.strftime("%Y%m%d")
        return str(value)


class CorteAhorroVistaResponse(BaseModel):
    periodo: str
    fecha_corte: str | None
    total_filas: int = Field(ge=0)
    numero_transacciones_mes: int = Field(ge=0)
    saldo: float


class ReporteAhorroVistaRangoResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    total_transacciones_mes: int = Field(ge=0)
    total_saldo: float
    cortes: list[CorteAhorroVistaResponse]
    filas: list[ReporteAhorroVistaFila]
