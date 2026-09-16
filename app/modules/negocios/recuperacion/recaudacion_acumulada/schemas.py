from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _normalizar_lista(valores: list[str]) -> list[str]:
    normalizados: list[str] = []
    vistos: set[str] = set()
    for valor in valores:
        texto = valor.strip().upper()
        if not texto:
            raise ValueError("Los filtros no pueden contener valores vacíos.")
        if texto not in vistos:
            vistos.add(texto)
            normalizados.append(texto)
    return normalizados


class InputRecaudacionAcumulada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fecha_inicio: date
    fecha_fin: date
    agencias: list[str] = Field(min_length=1, examples=[["MATRIZ"]])
    asesores: list[str] = Field(default_factory=list, examples=[["ANA ASESORA"]])

    @field_validator("agencias", "asesores", mode="after")
    @classmethod
    def normalizar_filtros(cls, valores: list[str]) -> list[str]:
        return _normalizar_lista(valores)

    @model_validator(mode="after")
    def validar_rango(self) -> "InputRecaudacionAcumulada":
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio.")
        if (self.fecha_inicio.year, self.fecha_inicio.month) != (
            self.fecha_fin.year,
            self.fecha_fin.month,
        ):
            raise ValueError("El rango de consulta debe estar dentro del mismo mes.")
        return self


class InputAsesoresPorAgencia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids_agencia: list[int] = Field(min_length=1)

    @field_validator("ids_agencia", mode="after")
    @classmethod
    def normalizar_ids(cls, valores: list[int]) -> list[int]:
        if any(valor <= 0 for valor in valores):
            raise ValueError("Los identificadores de agencia deben ser mayores que cero.")
        return list(dict.fromkeys(valores))


class AsesorAgenciaResponse(BaseModel):
    codigo: str
    nombre: str
    id_agencia: int
    agencia: str
    id_cargo: int
    cargo: str


class InformacionPersonaRecaudacion(BaseModel):
    identificacion: str = ""
    provincia: str = ""
    canton: str = ""
    parroquia: str = ""
    direccion: str = ""
    telefonos: str = ""


class GaranteRecaudacion(InformacionPersonaRecaudacion):
    nombres: str = ""


class PrestamoRecaudadoAcumulado(BaseModel):
    socio: int | None = None
    agencia: str
    numero_prestamo: str
    codigo_usuario_asignado: str
    nombre_usuario_asignado: str
    nombre: str

    estado_anterior: str
    estado_actual: str
    calificacion_anterior: str
    calificacion_actual: str
    dias_mora_anterior: int
    dias_mora_actual: int
    variacion_dias_mora: int
    saldo_capital_anterior: float
    saldo_capital_actual: float
    variacion_saldo_capital: float

    numero_cuota_actual_no_pagada: int | None = None
    numero_cuota_siguiente: int | None = None
    cobro_para_bajar_una_cuota: float
    cuotas_pendientes: int
    cuotas_pagadas: int
    total_cuotas: int

    calificacion_con_cobro_una_cuota: str
    dias_mora_con_cobro_una_cuota: int
    saldo_capital_con_cobro_una_cuota: float
    provision_con_cobro_una_cuota: float

    provision_cierre_mes: float
    provision_actual: float
    variacion_provisiones: float

    dia_ultimo_pago: date | None = None
    total_recuperado: float
    pendiente_pago: float
    pendiente_pago_mas_cuota_por_vencer: float
    total_a_cancelar: float

    informacion_deudor: InformacionPersonaRecaudacion | None = None
    garante_1: GaranteRecaudacion | None = None
    garante_2: GaranteRecaudacion | None = None


class RecaudacionAcumuladaResponse(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    total_registros: int
    total_recuperado: float
    prestamos: list[PrestamoRecaudadoAcumulado]
