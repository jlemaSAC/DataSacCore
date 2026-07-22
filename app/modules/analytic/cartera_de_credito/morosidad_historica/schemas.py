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


class MorosidadHistoricaAgrupacion(BaseModel):
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
    tasa_real: str
    plazo: str
    saldo_capital: float
    cartera_improductiva: float
    provision_requerida: float


class MorosidadHistoricaResponse(BaseModel):
    agrupaciones: list[MorosidadHistoricaAgrupacion]
