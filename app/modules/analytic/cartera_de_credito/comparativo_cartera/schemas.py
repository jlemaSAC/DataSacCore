from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.prestamos.normalizadores import normalizar_texto


class InputComparativoCartera(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_desde: date = Field(description="Primera fecha de corte incluida.")
    fecha_hasta: date = Field(description="Ultima fecha de corte incluida.")
    agencias: list[str] = Field(
        default_factory=list,
        description="Nombres de agencias. Una lista vacia consulta el consolidado.",
    )
    filtrar_diferidos: bool | None = Field(
        default=None,
        description="True: solo diferidos; false: sin diferidos; null: todos.",
    )

    @field_validator("agencias")
    @classmethod
    def normalizar_agencias(cls, value: list[str]) -> list[str]:
        return list(
            dict.fromkeys(
                agencia
                for item in value
                if (agencia := normalizar_texto(item))
            )
        )

    @model_validator(mode="after")
    def validar_rango(self) -> "InputComparativoCartera":
        if self.fecha_hasta < self.fecha_desde:
            raise ValueError("fecha_hasta no puede ser menor que fecha_desde.")
        if (
            self.fecha_desde.year,
            self.fecha_desde.month,
        ) != (
            self.fecha_hasta.year,
            self.fecha_hasta.month,
        ):
            raise ValueError("fecha_desde y fecha_hasta deben pertenecer al mismo mes.")
        return self


class CorteComparativoCartera(BaseModel):
    fecha_corte: date
    operaciones: int
    saldo_capital: float
    capital_vigente: float
    capital_no_devenga: float
    capital_vencido: float
    cartera_improductiva: float
    provision_requerida: float
    morosidad: float = Field(description="Indice de morosidad en escala decimal.")
    morosidad_porcentaje: float


class PuntoComparativoCartera(BaseModel):
    fecha: date
    actual: CorteComparativoCartera | None
    mes_anterior: CorteComparativoCartera | None = Field(
        description="Corte del ultimo dia del mes anterior al rango consultado."
    )
    anio_anterior: CorteComparativoCartera | None = Field(
        description="Corte del 31 de diciembre del anio anterior al rango consultado."
    )


class ResumenMorosidadRango(BaseModel):
    fecha_desde: date | None
    fecha_hasta: date | None
    dias_con_datos: int
    morosidad_inicial_porcentaje: float | None
    morosidad_final_porcentaje: float | None
    morosidad_promedio_ponderada_porcentaje: float | None = Field(
        description="Promedio del rango ponderado por el saldo capital de cada corte."
    )
    morosidad_minima_porcentaje: float | None
    morosidad_maxima_porcentaje: float | None
    variacion_puntos_porcentuales: float | None


class ComparativoMorosidadRango(BaseModel):
    actual: ResumenMorosidadRango
    mes_anterior: ResumenMorosidadRango
    anio_anterior: ResumenMorosidadRango


class ResumenCarteraAgencia(BaseModel):
    agencia: str
    saldo_capital: float
    morosidad_porcentaje: float
    cartera_improductiva: float
    provision_requerida: float


class ComparativoCarteraResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    consolidado: bool
    agencias: list[str]
    filtrar_diferidos: bool | None
    resumen_morosidad: ComparativoMorosidadRango
    resumen_por_agencia: list[ResumenCarteraAgencia] = Field(default_factory=list)
    puntos: list[PuntoComparativoCartera]
