from dataclasses import dataclass


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
    plazo: str


@dataclass
class ColocacionAgrupada:
    dimensiones: DimensionesColocacion
    operaciones: int
    saldo_inicial: float
