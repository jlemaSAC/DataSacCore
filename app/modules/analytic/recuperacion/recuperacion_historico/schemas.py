from datetime import date
from pydantic import BaseModel, ConfigDict, Field, model_validator


class InputRecuperacionHistoricoRango(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_desde: date = Field(description="Primera fecha de cobro incluida.")
    fecha_hasta: date = Field(description="Última fecha de cobro incluida.")

    @model_validator(mode="after")
    def validar_rango(self) -> "InputRecuperacionHistoricoRango":
        if self.fecha_hasta < self.fecha_desde:
            raise ValueError("fecha_hasta no puede ser menor que fecha_desde.")
        return self


class ResumenMensualRecuperacion(BaseModel):
    periodo: str
    anio: int
    mes: int
    fecha_desde: date
    fecha_hasta: date
    total_recuperado: float


class RecuperacionHistoricoAgrupacion(BaseModel):
    periodo: str
    anio: int
    mes: int
    estado_prestamo_inicio: str | None = None
    estado_prestamo_fin: str | None = None
    tipo_cobro: str | None = None
    tipo_transaccion: str | None = None
    agencia: str | None = None
    condicion: str | None = None
    tipo_prestamo: str | None = None
    producto: str | None = None
    segmento: str | None = None
    asesor: str | None = None
    provincia: str | None = None
    canton: str | None = None
    parroquia: str | None = None
    educacion: str | None = None
    edad: str | None = None
    garantia: str | None = None
    monto: str | None = None
    tasa: str | None = None
    tasa_valor: float | None = None
    tasa_real: str | None = None
    tasa_real_valor: float | None = None
    plazo: str | None = None
    plazo_valor: int | None = None
    total_recuperado: float


class RecuperacionHistoricoRangoResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    total_recuperado: float
    resumen_mensual: list[ResumenMensualRecuperacion]
    agrupaciones: list[RecuperacionHistoricoAgrupacion]
