from dataclasses import dataclass
from typing import Literal


DimensionFiltroColocacion = Literal[
    "agencia",
    "asesor",
    "tipo_prestamo",
    "producto",
    "segmento",
    "condicion",
    "tasa_normal",
    "tasa_real",
]


@dataclass(frozen=True, order=True)
class DimensionesColocacion:
    periodo: str
    anio: int
    mes: int
    agencia: str
    condicion: str
    tipo_prestamo: str
    producto: str
    segmento: str
    asesor: str
    provincia: str
    canton: str
    parroquia: str
    educacion: str
    edad: str
    garantia: str
    monto: str
    tasa: str
    tasa_valor: float | None
    tasa_real: str
    tasa_real_valor: float | None
    plazo: str
    plazo_valor: int | None


@dataclass
class ColocacionAgrupada:
    dimensiones: DimensionesColocacion
    operaciones: int
    saldo_inicial: float


@dataclass(frozen=True)
class DetalleColocacion:
    numero_cliente: str
    nombre_cliente: str
    numero_operacion: str
    agencia: str
    asesor: str
    tipo_condicion: str
    producto: str
    tipo_prestamo: str
    segmento: str
    tasa_nominal: float | None
    tasa_real: float | None
    monto_colocado: float


@dataclass(frozen=True)
class ResultadoDetalleColocacion:
    """Página parcial y totales calculados por una fuente de colocación."""

    items: list[DetalleColocacion]
    total_registros: int
    total_monto_colocado: float
