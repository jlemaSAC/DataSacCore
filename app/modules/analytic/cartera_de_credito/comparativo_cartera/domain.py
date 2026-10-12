from dataclasses import dataclass
from datetime import date
from typing import Literal


DimensionCartera = Literal[
    "agencia", "asesor", "usuario_responsable_control", "calificacion",
    "provincia", "producto", "tipo_prestamo", "cargo_asesor",
]


@dataclass(frozen=True)
class TotalesCartera:
    fecha_corte: date
    operaciones: int
    saldo_capital: float
    capital_vigente: float
    capital_no_devenga: float
    capital_vencido: float
    provision_requerida: float

    @property
    def cartera_improductiva(self) -> float:
        return self.capital_no_devenga + self.capital_vencido

    @property
    def morosidad(self) -> float:
        if not self.saldo_capital:
            return 0.0
        return self.cartera_improductiva / self.saldo_capital


@dataclass(frozen=True)
class PrestamoResumenCartera:
    numero_prestamo: str
    cliente: str | None
    dimensiones: dict[DimensionCartera, str]
    saldo_capital: float
    cartera_improductiva: float
    provision_requerida: float
