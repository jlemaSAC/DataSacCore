from dataclasses import dataclass


@dataclass(frozen=True)
class CorteActualMorosidad:
    fecha_corte: str
    anio: int
    mes: int


@dataclass(frozen=True, order=True)
class DimensionesMorosidad:
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
    tasa_real: str
    plazo: str
    cuota: str


@dataclass
class MorosidadAgrupada:
    dimensiones: DimensionesMorosidad
    saldo_capital: float
    cartera_improductiva: float
    provision_requerida: float
