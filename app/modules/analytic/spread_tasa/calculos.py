from decimal import Decimal

from app.modules.analytic.spread_tasa.constants import (
    CARTERA_POR_VENCER, INTERESES_CARTERA, MICROCREDITO_POR_VENCER, ZERO,
)

PRODUCTOS_RENDIMIENTO = {
    'microcredito': ('Microcrédito por Vencer', ('510420',), MICROCREDITO_POR_VENCER),
    'consumo': ('Crédito Consumo por Vencer', ('510410',), ('1402',)),
    'inmobiliario': ('Inmobiliario por Vencer', ('510415',), ('1403',)),
    'cartera': ('Cartera por Vencer', INTERESES_CARTERA, CARTERA_POR_VENCER),
}


def componentes_rendimientos(saldos: dict, promedios: dict, mes: int) -> dict:
    resultado = {}
    for producto, (_, cuentas_interes, cuentas_cartera) in PRODUCTOS_RENDIMIENTO.items():
        intereses = sum((saldos.get(c, ZERO) for c in cuentas_interes), ZERO)
        promedio = sum((promedios.get(c, ZERO) for c in cuentas_cartera), ZERO)
        resultado[producto] = {
            'intereses': intereses, 'saldo_promedio': promedio,
            'rendimiento': intereses / promedio * Decimal(12) / Decimal(mes) if promedio else None,
        }
    return resultado
