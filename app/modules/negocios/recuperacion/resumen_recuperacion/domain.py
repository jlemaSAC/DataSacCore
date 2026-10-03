from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class RecuperacionDiaria:
    fecha: date
    montos: dict[str, Decimal]
