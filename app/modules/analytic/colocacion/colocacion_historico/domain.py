from dataclasses import dataclass
from datetime import date
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


@dataclass
class TotalesResumenColocacion:
    """Acumulados mínimos para construir el resumen de Negocios."""

    operaciones: int = 0
    saldo_inicial: float = 0.0
    suma_tasa_nominal: float = 0.0
    operaciones_tasa_nominal: int = 0
    suma_tasa_real: float = 0.0
    operaciones_tasa_real: int = 0


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
class PrestamoAdjudicado:
    """Detalle de una operación adjudicada para los tableros de Negocios."""

    numero_operacion: str
    producto: str
    valor: float
    agencia: str
    tipo_prestamo: str
    asesor: str
    fecha_adjudicacion: date


@dataclass(frozen=True)
class ResultadoDetalleColocacion:
    """Página parcial y totales calculados por una fuente de colocación."""

    items: list[DetalleColocacion]
    total_registros: int
    total_monto_colocado: float
