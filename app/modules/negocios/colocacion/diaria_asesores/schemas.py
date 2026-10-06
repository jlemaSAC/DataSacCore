from datetime import date

from pydantic import BaseModel, Field


class ColocacionIndicadores(BaseModel):
    operaciones: int
    monto_colocado: float


class ColocacionAsesorComparativo(BaseModel):
    codigo_usuario: str
    asesor: str
    hoy: ColocacionIndicadores
    ayer: ColocacionIndicadores
    cambio: ColocacionIndicadores


class ColocacionResumenComparativo(BaseModel):
    hoy: ColocacionIndicadores
    ayer: ColocacionIndicadores
    cambio: ColocacionIndicadores


class ColocacionDiariaAsesoresResponse(BaseModel):
    fecha: date
    fecha_ayer: date
    id_agencia: int
    agencia: str
    resumen: ColocacionResumenComparativo
    asesores: list[ColocacionAsesorComparativo] = Field(default_factory=list)
