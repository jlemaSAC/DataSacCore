from dataclasses import dataclass


@dataclass(frozen=True)
class DatosOperativosRecuperacion:
    numero_prestamo: str
    socio: int | None
    nombre: str
    estado_prestamo: str
    calificacion_actual: str
    saldo_capital: float
    pendiente_pago: float
    valor_al_dia_mas_cuota_actual: float
    cuotas_pagadas: int
    total_cuotas: int
    es_diferido: bool
