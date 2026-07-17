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
    anio: int
    mes: int
    numero_prestamo: str
    tipo_cobro: str
    tipo_transaccion: str
    valor_recuperado: float
    agencia: str
    asesor: str
    abogado_externo: str
    nombre_cobranza_apoyo: str
    estado_prestamo_anterior_cobro: str
    estado_prestamo_actual_cobro: str
    calificacion_anterior_cobro: str
    calificacion_actual_cobro: str
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
    calificacion_inicio: str = "SIN DATOS"
    calificacion_fin: str = "SIN DATOS"


class RecuperacionHistoricoRangoResponse(BaseModel):
    prestamos_por_numero: dict[str, PrestamoRecuperacionOut]
    recuperaciones: list[RecuperacionEtiquetadaOut]
