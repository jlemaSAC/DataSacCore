from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


class CorteCastigoNoDisponibleError(ValueError):
    """No se puede calcular una diferencia diaria sin sus cortes de origen."""


@dataclass(frozen=True)
class PrestamoCastigoInicio:
    numero_prestamo: str
    estado: str
    agencia: str
    codigo_asesor: str
    asesor: str
    cargo: str


@dataclass(frozen=True)
class CorteDepositosCastigo:
    numero_prestamo: str
    fecha: date
    depositos_mes: Decimal
    estado: str


@dataclass(frozen=True)
class CortesDepositosCastigo:
    prestamos: list[PrestamoCastigoInicio]
    cortes: list[CorteDepositosCastigo]
    fecha_sql: date | None = None
    estados_actuales: dict[str, str] = field(default_factory=dict)


def normalizar_estado(valor: object) -> str:
    texto = str(valor or "").strip().upper()
    return {
        "CASTIGO": "CASTIGADO", "T": "CASTIGADO", "J": "JUDICIAL", "C": "CANCELADO",
    }.get(texto, texto)
