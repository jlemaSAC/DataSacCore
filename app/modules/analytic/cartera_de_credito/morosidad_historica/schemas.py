from pydantic import BaseModel, ConfigDict, Field, model_validator


class InputMorosidadHistorica(BaseModel):
    model_config = ConfigDict(extra="forbid")

    periodo_desde: str = Field(
        pattern=r"^[1-9]\d{3}-(0[1-9]|1[0-2])$",
        examples=["2025-01"],
        description="Primer mes incluido, en formato YYYY-MM.",
    )
    periodo_hasta: str = Field(
        pattern=r"^[1-9]\d{3}-(0[1-9]|1[0-2])$",
        examples=["2025-12"],
        description="Ultimo mes incluido, en formato YYYY-MM.",
    )

    @model_validator(mode="after")
    def validar_rango(self) -> "InputMorosidadHistorica":
        if self.periodo_hasta < self.periodo_desde:
            raise ValueError("periodo_hasta no puede ser menor que periodo_desde.")
        return self


class ValoresMorosidad(BaseModel):
    operaciones: int
    saldo_capital: float
    capital_vigente: float
    capital_no_devenga: float
    capital_vencido: float
    cartera_improductiva: float
    morosidad: float = Field(description="Cartera improductiva / saldo de capital.")
    morosidad_porcentaje: float


class ResumenMensualMorosidad(ValoresMorosidad):
    periodo: str
    anio: int
    mes: int
    fecha_corte: str = Field(description="Corte consultado en formato YYYYMMDD.")


class MorosidadHistoricaAgrupacion(ValoresMorosidad):
    periodo: str
    anio: int
    mes: int
    agencia: str
    condicion: str
    tipo_prestamo: str
    producto: str
    segmento: str
    asesor: str
    provincia: str
    canton: str
    parroquia: str
    educacion: str
    edad: str
    garantia: str
    monto: str
    tasa: str
    tasa_valor: float | None
    tasa_real: str
    tasa_real_valor: float | None
    plazo: str
    plazo_valor: int | None


class MorosidadHistoricaResponse(ValoresMorosidad):
    periodo_desde: str
    periodo_hasta: str
    resumen_mensual: list[ResumenMensualMorosidad]
    agrupaciones: list[MorosidadHistoricaAgrupacion]
    periodos_sin_datos: list[str]

