from app.modules.analytic.analisis_contable.calculos_resultados import (
    MARGEN_NETO_INTERESES, MARGEN_BRUTO_FINANCIERO, MARGEN_FINANCIERO_NETO,
    MARGEN_INTERMEDIACION, MARGEN_OPERACIONAL, GANANCIA_ANTES_IMPUESTOS, GANANCIA_EJERCICIO,
)


# Orden de presentación del estado de resultados. Las cuentas de gasto conservan
# su saldo positivo: el signo indica cómo intervienen en el siguiente subtotal.
FILAS = (
    ("ingresos", "5", "", "Ingresos", (("5", 1),)),
    ("intereses_ganados", "51", "", "Intereses y descuentos ganados", (("51", 1),)),
    ("intereses_causados", "41", "-", "Intereses causados", (("41", 1),)),
    ("margen_neto_intereses", None, "", "MARGEN NETO DE INTERESES", MARGEN_NETO_INTERESES),
    ("comisiones_ganadas", "52", "+", "Comisiones ganadas", (("52", 1),)),
    ("ingresos_servicios", "54", "+", "Ingresos por servicios", (("54", 1),)),
    ("comisiones_causadas", "42", "-", "Comisiones causadas", (("42", 1),)),
    ("utilidades_financieras", "53", "+", "Utilidades financieras", (("53", 1),)),
    ("perdidas_financieras", "43", "-", "Pérdidas financieras", (("43", 1),)),
    ("margen_bruto_financiero", None, "", "MARGEN BRUTO FINANCIERO", MARGEN_BRUTO_FINANCIERO),
    ("provisiones", "44", "-", "Provisiones", (("44", 1),)),
    ("margen_financiero_neto", None, "", "MARGEN NETO FINANCIERO", MARGEN_FINANCIERO_NETO),
    ("gastos_operacion", "45", "-", "Gastos de operación", (("45", 1),)),
    ("margen_intermediacion", None, "", "MARGEN DE INTERMEDIACIÓN", MARGEN_INTERMEDIACION),
    ("otros_ingresos_operacionales", "55", "+", "Otros ingresos operacionales", (("55", 1),)),
    ("otras_perdidas_operacionales", "46", "-", "Otras pérdidas operacionales", (("46", 1),)),
    ("margen_operacional", None, "", "MARGEN OPERACIONAL", MARGEN_OPERACIONAL),
    ("otros_ingresos", "56", "+", "Otros ingresos", (("56", 1),)),
    ("otros_gastos_perdidas", "47", "-", "Otros gastos y pérdidas", (("47", 1),)),
    ("ganancia_antes_impuestos", None, "", "GANANCIA ANTES DE IMPUESTOS", GANANCIA_ANTES_IMPUESTOS),
    ("impuestos_participacion", "48", "-", "Impuestos y participación a empleados", (("48", 1),)),
    ("ganancia_ejercicio", None, "", "GANANCIA O PÉRDIDA DEL EJERCICIO", GANANCIA_EJERCICIO),
)
CUENTAS = tuple(dict.fromkeys(cuenta for *_, terminos in FILAS for cuenta, _ in terminos))
