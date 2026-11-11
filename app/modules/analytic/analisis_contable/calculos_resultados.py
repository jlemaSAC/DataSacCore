from decimal import Decimal

from app.modules.contabilidad.repositories.sql_saldo_contable_repository import MAPA_NETEO_CUENTAS


MARGEN_NETO_INTERESES = (("51", 1), ("41", -1))
MARGEN_BRUTO_FINANCIERO = (*MARGEN_NETO_INTERESES, ("52", 1), ("54", 1), ("42", -1), ("53", 1), ("43", -1))
MARGEN_FINANCIERO_NETO = (*MARGEN_BRUTO_FINANCIERO, ("44", -1))
MARGEN_INTERMEDIACION = (*MARGEN_FINANCIERO_NETO, ("45", -1))
MARGEN_OPERACIONAL = (*MARGEN_INTERMEDIACION, ("55", 1), ("46", -1))
GANANCIA_ANTES_IMPUESTOS = (*MARGEN_OPERACIONAL, ("56", 1), ("47", -1))
GANANCIA_EJERCICIO = (*GANANCIA_ANTES_IMPUESTOS, ("48", -1))


def calcular_indicador(definicion, saldos, neteo):
    codigo, nombre, terminos = definicion
    partes = []
    for cuenta, coeficiente in terminos:
        ajuste = MAPA_NETEO_CUENTAS.get(cuenta) if neteo else None
        expresion = f"{cuenta} - {ajuste}" if ajuste else cuenta
        if ajuste and len(terminos) > 1:
            expresion = f"({expresion})"
        partes.append((" + " if coeficiente > 0 else " - ") + expresion if partes else expresion)
    saldo = None if any(saldos.get(cuenta) is None for cuenta, _ in terminos) else sum(
        (saldos[cuenta] * coeficiente for cuenta, coeficiente in terminos), Decimal("0.00")
    )
    return dict(codigo=codigo, nombre=nombre, formula="".join(partes), saldo=saldo)


