from datetime import date

from pydantic import BaseModel, Field

from app.modules.negocios.inversiones.depositos_a_plazo.schemas import (
    MetricasDepositos,
    ResumenActualDepositosResponse,
)


class AsesorResumenDepositos(MetricasDepositos):
    asesor: str


class PeriodicidadResumenDepositos(MetricasDepositos):
    periodicidad_pago: str


class CondicionResumenDepositos(MetricasDepositos):
    condicion: str


class DiaResumenDepositos(BaseModel):
    fecha: date
    monto_total: float
    numero_operaciones: int = Field(ge=0)
    monto_por_condicion: dict[str, float]


class ResumenDepositosAPlazoResponse(ResumenActualDepositosResponse):
    por_asesor: list[AsesorResumenDepositos]
    por_periodicidad: list[PeriodicidadResumenDepositos]
    por_condicion: list[CondicionResumenDepositos]
    diario: list[DiaResumenDepositos] = Field(
        description=(
            "DPF del universo al corte, agrupados por fecha de creación dentro del rango. "
            "No incluye depósitos cancelados antes del corte. Los días sin ingresos tienen cero."
        )
    )
