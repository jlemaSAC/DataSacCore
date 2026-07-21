from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RecuperacionEtiquetada:
    fecha_cobro: date
    numero_prestamo: str
    tipo_cobro: str
    tipo_transaccion: str
    valor_recuperado: float
    agencia: str = "SIN DATOS"
    asesor: str = "SIN DATOS"
    abogado_externo: str = "SIN DATOS"
    nombre_cobranza_apoyo: str = "SIN DATOS"
    estado_prestamo_anterior_cobro: str = "SIN DATOS"
    estado_prestamo_actual_cobro: str = "SIN DATOS"
    calificacion_anterior_cobro: str = "SIN DATOS"
    calificacion_actual_cobro: str = "SIN DATOS"


@dataclass(frozen=True)
class PrestamoRecuperacion:
    """Dimensiones del corte final y estados de ambos extremos del rango."""

    numero_prestamo: str
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
    edad: int | None
    garantia: str
    monto: float | None
    tasa: float | None
    tasa_real: float | None
    plazo: int | None
    estado_prestamo_inicio: str
    estado_prestamo_fin: str
    calificacion_inicio: str = "SIN DATOS"
    calificacion_fin: str = "SIN DATOS"
