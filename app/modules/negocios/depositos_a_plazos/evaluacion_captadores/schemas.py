from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.schemas import (
    SituacionCrediticiaAgenciaGerenteItem,
)


class EvaluacionCaptadoresRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date
    fecha_fin: date
    id_agencia: int = Field(default=0, ge=0, description="0 para consolidado.")

    @model_validator(mode="after")
    def validar_rango(self) -> "EvaluacionCaptadoresRequest":
        if self.fecha_inicio > self.fecha_fin:
            raise ValueError("fecha_inicio no puede ser posterior a fecha_fin.")
        if (self.fecha_inicio.year, self.fecha_inicio.month) != (
            self.fecha_fin.year, self.fecha_fin.month
        ):
            raise ValueError("fecha_inicio y fecha_fin deben pertenecer al mismo mes.")
        return self


class CaptadorValores(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    saldo_deposito: float = Field(alias="SaldoDeposito")
    tasa_promedio: float | None = Field(alias="TasaPromedio")
    operaciones: int = Field(alias="Operaciones", ge=0)
    tasa_promedio_renovacion: float | None = Field(alias="TasaPromedioRenovacion")
    suma_tasas: float = Field(alias="SumaTasas", description="Permite reagrupar el promedio por operación.")
    operaciones_renovacion: int = Field(alias="OperacionesRenovacion", ge=0)
    suma_tasas_renovacion: float = Field(alias="SumaTasasRenovacion")


class CaptadorVariacion(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    saldo_deposito: float = Field(alias="SaldoDeposito")
    tasa_promedio: float | None = Field(alias="TasaPromedio")
    operaciones: int = Field(alias="Operaciones")
    tasa_promedio_renovacion: float | None = Field(alias="TasaPromedioRenovacion")


class CaptadorComparacion(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    clave: str = Field(alias="Clave", description="Código de usuario y agencia.")
    codigo_usuario: str = Field(alias="CodigoUsuario")
    nombre_captador_actual: str | None = Field(alias="NombreCaptadorActual")
    nombre_captador_cierre_mes_anterior: str | None = Field(alias="NombreCaptadorCierreMesAnterior")
    cargo_captador_actual: str = Field(alias="CargoCaptadorActual")
    agencia_actual: str | None = Field(alias="AgenciaActual")
    agencia_cierre_mes_anterior: str | None = Field(alias="AgenciaCierreMesAnterior")
    valores_actual: CaptadorValores | None = Field(alias="ValoresActual")
    valores_cierre_mes_anterior: CaptadorValores | None = Field(alias="ValoresCierreMesAnterior")
    diferencias_cierre_mes_anterior: CaptadorVariacion = Field(alias="DiferenciasCierreMesAnterior")


class EvaluacionCaptadoresResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    fecha_corte_actual: date
    fecha_corte_cierre_mes_anterior: date
    comparacion: list[CaptadorComparacion]
    agencias_gerentes_oficina: list[SituacionCrediticiaAgenciaGerenteItem]
    faltantes_en_cierre_mes_anterior: list[str]
    faltantes_en_actual: list[str]
