from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InputRecuperacionHistoricoRango(BaseModel):
    """Rango de recuperación; la fuente de consulta es solo MongoDB."""

    model_config = ConfigDict(extra="forbid")

    fecha_desde: date = Field(description="Primera fecha de cobro incluida.")
    fecha_hasta: date = Field(description="Última fecha de cobro incluida.")

    @model_validator(mode="after")
    def validar_rango(self) -> "InputRecuperacionHistoricoRango":
        if self.fecha_hasta < self.fecha_desde:
            raise ValueError("fecha_hasta no puede ser menor que fecha_desde.")
        return self


class RecuperacionEtiquetadaOut(BaseModel):
    fecha_cobro: date
    periodo: str
    anio: int
    mes: int
    numero_prestamo: str
    tipo_cobro: str
    tipo_transaccion: str
    valor_recuperado: float
    agencia: str
    asesor: str
    abogado_externo: str
    codigo_cobranza_apoyo: str
    nombre_cobranza_apoyo: str
    estado_prestamo_cobro: str
    calificacion_cobro: str
    fecha_estado_prestamo_anterior_cobro: str
    estado_prestamo_anterior_cobro: str
    fecha_estado_prestamo_actual_cobro: str
    estado_prestamo_actual_cobro: str
    calificacion_anterior_cobro: str
    calificacion_actual_cobro: str
    es_cancelado_anterior_cobro: bool
    es_cancelado_actual_cobro: bool
    se_cancelo_con_el_cobro: bool


class PrestamoRecuperacionOut(BaseModel):
    numero_prestamo: str
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
    edad: int | None
    garantia: str
    monto: float | None = Field(description="Deuda inicial del préstamo en el corte final.")
    tasa: float | None = Field(description="Tasa nominal en el corte final.")
    tasa_real: float | None = Field(description="Tasa anual en el corte final.")
    plazo: int | None = Field(description="Plazo registrado en el corte final.")
    estado_prestamo_inicio: str
    estado_prestamo_fin: str


class ResumenMensualRecuperacion(BaseModel):
    periodo: str
    anio: int
    mes: int
    fecha_desde: date
    fecha_hasta: date
    total_recuperado: float


class RecuperacionHistoricoRangoResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    total_recuperado: float
    resumen_mensual: list[ResumenMensualRecuperacion]
    prestamos_por_numero: dict[str, PrestamoRecuperacionOut]
    recuperaciones: list[RecuperacionEtiquetadaOut]
