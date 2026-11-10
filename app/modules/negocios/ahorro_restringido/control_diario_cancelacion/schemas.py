from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ControlCancelacionRestringidosRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date = Field(ge=date(1900, 1, 1), le=date(9998, 12, 31))
    fecha_fin: date = Field(ge=date(1900, 1, 1), le=date(9998, 12, 31))
    id_agencia: int = Field(default=0, ge=0, description="0 para consolidado.")

    @model_validator(mode="after")
    def validar_rango(self) -> "ControlCancelacionRestringidosRequest":
        if self.fecha_inicio > self.fecha_fin:
            raise ValueError("fecha_inicio no puede ser posterior a fecha_fin.")
        if self.fecha_inicio.replace(day=1) != self.fecha_fin.replace(day=1):
            raise ValueError("Las fechas deben pertenecer al mismo mes.")
        return self


class CancelacionRestringidosDia(BaseModel):
    monto: float
    cuentas: int = Field(ge=0)


class CancelacionRestringidosFila(BaseModel):
    codigo_usuario: str
    nombre_asesor: str
    cargo: str
    id_agencia: int
    agencia: str
    codigo_producto: str
    producto_ahorro: str
    valores: list[CancelacionRestringidosDia]


class ControlCancelacionRestringidosResponse(ControlCancelacionRestringidosRequest):
    fecha_corte: date
    dias: list[date]
    filas: list[CancelacionRestringidosFila]


class DetalleCancelacionRestringidosRequest(ControlCancelacionRestringidosRequest):
    fecha: date | None = None
    codigo_usuario: str | None = Field(default=None, max_length=100)
    cargos: list[str] = Field(default_factory=list, max_length=100)
    productos: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("codigo_usuario")
    @classmethod
    def validar_usuario(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("codigo_usuario no puede estar vacío.")
        return value.strip() if value is not None else None

    @field_validator("cargos", "productos")
    @classmethod
    def normalizar_filtros(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("Los filtros no pueden contener valores vacíos.")
        return list(dict.fromkeys(item.strip().upper() for item in value))

    @model_validator(mode="after")
    def validar_fecha(self) -> "DetalleCancelacionRestringidosRequest":
        if self.fecha is not None and not self.fecha_inicio <= self.fecha <= self.fecha_fin:
            raise ValueError("fecha debe estar dentro del rango consultado.")
        return self


class DetalleCancelacionRestringidosItem(BaseModel):
    id_movimiento: int
    numero_cuenta: str
    numero_cliente: str
    nombre_cliente: str
    codigo_usuario: str
    nombre_asesor: str
    cargo: str
    id_agencia: int
    agencia: str
    codigo_producto: str
    producto_ahorro: str
    fecha_cancelacion: date
    monto: float


class DetalleCancelacionRestringidosResponse(DetalleCancelacionRestringidosRequest):
    fecha_corte: date
    total_registros: int
    total_monto: float
    items: list[DetalleCancelacionRestringidosItem]
