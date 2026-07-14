from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RecuperacionAgrupada:
    periodo: str
    anio: int
    mes: int
    dimensiones: dict[str, Any]
    total_recuperado: float
