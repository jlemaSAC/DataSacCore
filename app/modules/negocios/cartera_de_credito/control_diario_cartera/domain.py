from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class CorteAsesor:
    fecha: date
    codigo_asesor: str
    nombre_asesor: str
    cargo: str
    agencia: str
    saldo_capital: Decimal
    cartera_improductiva: Decimal
    provisiones: Decimal


@dataclass(frozen=True)
class CortesControlCartera:
    fechas: set[date]
    asesores: list[CorteAsesor]


class ControlDiarioCarteraRepository(Protocol):
    def obtener_cortes(
        self, *, desde: date, hasta: date, agencia: str | None,
        filtrar_diferidos: bool | None,
    ) -> CortesControlCartera: ...
