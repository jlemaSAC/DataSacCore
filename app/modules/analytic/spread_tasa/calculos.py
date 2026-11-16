from decimal import Decimal

from app.modules.analytic.spread_tasa.constants import (
    CARTERA_POR_VENCER, FUENTES_FONDEO, INTERESES_CARTERA, MICROCREDITO_POR_VENCER, ZERO,
)

PRODUCTOS_RENDIMIENTO = {
    'microcredito': ('Microcrédito por Vencer', ('510420',), MICROCREDITO_POR_VENCER),
    'consumo': ('Crédito Consumo por Vencer', ('510410',), ('1402',)),
    'inmobiliario': ('Inmobiliario por Vencer', ('510415',), ('1403',)),
    'cartera': ('Cartera por Vencer', INTERESES_CARTERA, CARTERA_POR_VENCER),
}

TIPOS_COSTO = {
    'ahorro_plazo': ('Costo Ahorro Plazo', ('410130',), ('2103',)),
    'ahorro_vista': ('Costo Ahorro Vista', ('410115',), ('2101',)),
    'obligaciones_financieras': ('Costo Obligaciones Financieras', ('4103',), ('26',)),
    'promedio_fondeo': ('Costo Promedio de Fondeo', ('41',), FUENTES_FONDEO),
}


def _componentes(saldos: dict, promedios: dict, mes: int, definiciones: dict, campo_valor: str) -> dict:
    resultado = {}
    for indicador, (_, cuentas_interes, cuentas_promedio) in definiciones.items():
        intereses = sum((saldos.get(c, ZERO) for c in cuentas_interes), ZERO)
        promedio = sum((promedios.get(c, ZERO) for c in cuentas_promedio), ZERO)
        resultado[indicador] = {
            'intereses': intereses, 'saldo_promedio': promedio,
            campo_valor: intereses / promedio * Decimal(12) / Decimal(mes) if promedio else None,
        }
    return resultado


def componentes_rendimientos(saldos: dict, promedios: dict, mes: int) -> dict:
    return _componentes(saldos, promedios, mes, PRODUCTOS_RENDIMIENTO, 'rendimiento')


def componentes_costos(saldos: dict, promedios: dict, mes: int) -> dict:
    return _componentes(saldos, promedios, mes, TIPOS_COSTO, 'costo')
