from datetime import date

from pydantic import BaseModel, Field


class CarteraIndicadores(BaseModel):
    operaciones: int
    creditos_en_mora: int
    creditos_dias_vencidos_1: int
    saldo_capital: float
    provision_requerida: float
    morosidad_monto: float
    morosidad_porcentaje: float = Field(
        description="En el bloque cambio, representa puntos porcentuales."
    )


class CarteraDiariaAsesor(BaseModel):
    codigo_usuario: str
    asesor: str
    operaciones: int
    creditos_en_mora: int
    creditos_dias_vencidos_1: int
    saldo_capital: float
    provision_requerida: float
    morosidad_monto: float
    morosidad_porcentaje: float


class ResumenCarteraSnapshot(BaseModel):
    fecha: date
    operaciones: int
    creditos_en_mora: int
    creditos_dias_vencidos_1: int
    saldo_capital: float
    provision_requerida: float
    morosidad_monto: float
    morosidad_porcentaje: float
    asesores: list[CarteraDiariaAsesor] = Field(default_factory=list)


class AsesorCarteraComparativo(BaseModel):
    codigo_usuario: str
    asesor: str
    hoy: CarteraIndicadores
    ayer: CarteraIndicadores | None = None
    cambio: CarteraIndicadores | None = None


class ResumenCarteraComparativo(BaseModel):
    hoy: CarteraIndicadores
    ayer: CarteraIndicadores | None = None
    cambio: CarteraIndicadores | None = None


class ResumenDiarioCarteraAsesoresResponse(BaseModel):
    fecha: date
    fecha_ayer: date
    id_agencia: int
    agencia: str
    resumen: ResumenCarteraComparativo
    asesores: list[AsesorCarteraComparativo] = Field(default_factory=list)
