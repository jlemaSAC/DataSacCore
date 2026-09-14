from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RecuperacionPrestamo:
    numero_prestamo: str
    fecha_ultimo_pago: date | None
    total_recuperado: float


@dataclass(frozen=True)
class DetalleCuotaPrestamo:
    numero_prestamo: str
    socio: int | None = None
    nombre: str = ""
    identificacion: str = ""
    provincia: str = ""
    canton: str = ""
    parroquia: str = ""
    direccion: str = ""
    telefonos: str = ""
    numero_cuota_actual_no_pagada: int | None = None
    numero_cuota_siguiente: int | None = None
    cobro_hasta_cuota: float = 0.0
    cuotas_pendientes: int = 0
    calificacion_con_cobro_una_cuota: str = "A-1"
    dias_mora_con_cobro_una_cuota: int = 0
    saldo_capital_con_cobro_una_cuota: float = 0.0
    cuotas_pagadas: int = 0
    total_cuotas: int = 0
    porcentaje_fijo: float | None = None
    porcentaje_minimo: float | None = None
    porcentaje_maximo: float | None = None
    es_porcentaje_fijo: bool | None = None
    garante_1: dict[str, str] | None = None
    garante_2: dict[str, str] | None = None
