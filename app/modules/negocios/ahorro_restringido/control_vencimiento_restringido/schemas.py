from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.schemas import (
    SituacionCrediticiaAgenciaGerenteItem,
)


class ControlVencimientoRestringidoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date = Field(description="Primer día de vencimiento, incluido.")
    fecha_fin: date = Field(description="Último día de vencimiento, incluido. Permite fechas futuras.")
    id_agencia: int = Field(default=0, ge=0, description="0 para consolidado.")

    @model_validator(mode="after")
    def validar_rango(self) -> "ControlVencimientoRestringidoRequest":
        if self.fecha_inicio > self.fecha_fin:
            raise ValueError("fecha_inicio no puede ser posterior a fecha_fin.")
        if self.fecha_fin == date.max:
            raise ValueError("fecha_fin debe ser anterior a 9999-12-31.")
        return self


class ControlVencimientoRestringidoFila(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    clave: str = Field(alias="Clave")
    codigo_usuario: str = Field(alias="CodigoUsuario")
    nombre_asesor: str = Field(alias="NombreAsesor")
    cargo: str = Field(alias="Cargo")
    codigo_producto: str = Field(alias="CodigoProducto")
    producto_ahorro: str = Field(alias="ProductoAhorro")
    id_agencia: int = Field(alias="IdAgencia")
    agencia: str = Field(alias="Agencia")
    saldo: float = Field(alias="Saldo", description="Saldo actual de las cuentas con contrato activo que vence dentro del rango.")


class ControlVencimientoRestringidoResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    id_agencia: int
    fecha_sistema: date
    saldo_total: float
    filas: list[ControlVencimientoRestringidoFila]
    agencias_gerentes_oficina: list[SituacionCrediticiaAgenciaGerenteItem]


class DetalleControlVencimientoRestringidoRequest(ControlVencimientoRestringidoRequest):
    codigo_usuario: str | None = Field(default=None, max_length=100)
    productos: list[str] = Field(default_factory=list, max_length=100)
    pagina: int = Field(default=1, ge=1)
    tamano_pagina: int = Field(default=100, ge=1, le=500)
    sin_paginacion: bool = Field(default=False, description="Devuelve todas las cuentas del filtro en una respuesta.")

    @field_validator("codigo_usuario")
    @classmethod
    def normalizar_codigo(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("codigo_usuario no puede estar vacío.")
        return value.strip()

    @field_validator("productos")
    @classmethod
    def normalizar_productos(cls, value: list[str]) -> list[str]:
        if any(not producto.strip() for producto in value):
            raise ValueError("productos no puede contener valores vacíos.")
        return list(dict.fromkeys(producto.strip() for producto in value))


class DetalleControlVencimientoRestringidoFila(BaseModel):
    id_programacion: int
    numero_cliente: str
    nombre_cliente: str
    agencia: str
    asesor: str
    numero_cuenta: str
    producto_ahorro: str
    saldo_actual: float
    tasa: float = Field(description="Tasa del contrato de ahorro programado activo.")
    tiene_prestamo: bool = Field(description="El cliente principal tiene un préstamo no cancelado con vínculo activo.")
    fecha_vencimiento: date
    estado: str


class DetalleControlVencimientoRestringidoResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    id_agencia: int
    codigo_usuario: str | None
    productos: list[str]
    pagina: int | None
    tamano_pagina: int | None
    total_registros: int
    total_saldo: float
    items: list[DetalleControlVencimientoRestringidoFila]
