from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.schemas import (
    SituacionCrediticiaAgenciaGerenteItem,
)


class ControlVencimientoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date = Field(description="Primer día de vencimiento, incluido.")
    fecha_fin: date = Field(description="Último día de vencimiento, incluido. Permite fechas futuras.")
    id_agencia: int = Field(default=0, ge=0, description="0 para consolidado.")

    @model_validator(mode="after")
    def validar_rango(self) -> "ControlVencimientoRequest":
        if self.fecha_inicio > self.fecha_fin:
            raise ValueError("fecha_inicio no puede ser posterior a fecha_fin.")
        if self.fecha_fin == date.max:
            raise ValueError("fecha_fin debe ser anterior a 9999-12-31.")
        return self


class ControlVencimientoFila(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    clave: str = Field(alias="Clave")
    codigo_usuario: str = Field(alias="CodigoUsuario")
    nombre_captador: str = Field(alias="NombreCaptador")
    cargo: str = Field(alias="Cargo")
    id_agencia: int = Field(alias="IdAgencia")
    agencia: str = Field(alias="Agencia")
    saldo: float = Field(alias="Saldo", description="Capital actual de los DPF que vencen dentro del rango.")


class ControlVencimientoResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    id_agencia: int
    fecha_sistema: date
    saldo_total: float
    filas: list[ControlVencimientoFila]
    agencias_gerentes_oficina: list[SituacionCrediticiaAgenciaGerenteItem]


class DetalleControlVencimientoRequest(ControlVencimientoRequest):
    codigo_usuario: str | None = Field(default=None, max_length=100)
    cargos: list[str] = Field(default_factory=list, max_length=100)
    pagina: int = Field(default=1, ge=1)
    tamano_pagina: int = Field(default=100, ge=1, le=500)
    sin_paginacion: bool = Field(default=False, description="Devuelve todos los DPF del filtro en una respuesta.")

    @field_validator("codigo_usuario")
    @classmethod
    def normalizar_codigo(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("codigo_usuario no puede estar vacío.")
        return value.strip()

    @field_validator("cargos")
    @classmethod
    def normalizar_cargos(cls, value: list[str]) -> list[str]:
        if any(not cargo.strip() for cargo in value):
            raise ValueError("cargos no puede contener valores vacíos.")
        return list(dict.fromkeys(cargo.strip() for cargo in value))


class DetalleControlVencimientoFila(BaseModel):
    id_deposito: int
    numero_cliente: str
    nombre_cliente: str
    agencia: str
    captador: str
    numero_deposito: str
    monto: float
    interes_total: float = Field(description="Interés calculado total, incluyendo el ya pagado.")
    tasa_total: float = Field(description="Tasa efectiva del DPF; incluye la variación una sola vez.")
    tiene_prestamo: bool = Field(description="El cliente principal tiene un préstamo no cancelado con vínculo activo.")
    fecha_vencimiento: date
    estado: str


class DetalleControlVencimientoResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    id_agencia: int
    codigo_usuario: str | None
    cargos: list[str]
    pagina: int | None
    tamano_pagina: int | None
    total_registros: int
    total_monto: float
    total_interes: float
    items: list[DetalleControlVencimientoFila]
