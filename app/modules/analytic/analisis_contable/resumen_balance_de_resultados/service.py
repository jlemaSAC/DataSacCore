from decimal import Decimal

from fastapi import HTTPException

from app.modules.analytic.analisis_contable.calculos_resultados import (
    MARGEN_NETO_INTERESES, MARGEN_BRUTO_FINANCIERO, MARGEN_FINANCIERO_NETO,
    MARGEN_INTERMEDIACION, calcular_indicador,
)

from app.modules.contabilidad.repositories.sql_saldo_contable_repository import MAPA_NETEO_CUENTAS
from app.modules.analytic.analisis_contable.resumen_balance_de_resultados.schemas import (
    ConsultaBalanceResultados,
    ResumenBalanceResultados,
    ValidacionUtilidad,
)


INDICADORES = (
    ("gastos", "Gastos", (("4", 1),)),
    ("intereses_causados", "Intereses Causados", (("41", 1),)),
    ("provisiones", "Provisiones", (("44", 1),)),
    ("gasto_operativo", "Gasto Operativo", (("45", 1),)),
    ("ingresos", "Ingresos", (("5", 1),)),
    ("intereses_ganados", "Intereses Ganados", (("51", 1),)),
    ("comisiones_ganadas", "Comisiones Ganadas", (("52", 1),)),
    ("utilidades_financieras", "Utilidades Financieras", (("53", 1),)),
    ("margen_intermediacion", "Margen de Intermediación", MARGEN_INTERMEDIACION),
    ("utilidad", "Utilidad", (("5", 1), ("4", -1))),
)
MARGENES = (
    ("margen_neto_intereses", "Margen Neto de Intereses", MARGEN_NETO_INTERESES),
    ("margen_bruto_financiero", "Margen Bruto Financiero", MARGEN_BRUTO_FINANCIERO),
    ("margen_financiero_neto", "Margen Financiero Neto", MARGEN_FINANCIERO_NETO),
    ("margen_intermediacion", "Margen de Intermediación", MARGEN_INTERMEDIACION),
)
CUENTAS = tuple(dict.fromkeys(cuenta for _, _, terminos in INDICADORES for cuenta, _ in terminos))
CUENTAS_VALIDACION = ("1", "2", "3", "5", "4")


def validar_utilidad(saldos_base, utilidad) -> ValidacionUtilidad:
    # Se concilian saldos sin neteo: las transferencias internas por agencia pueden
    # cambiar el resultado mostrado aunque la ecuación contable original cuadre.
    faltantes = [cuenta for cuenta in CUENTAS_VALIDACION if saldos_base.get(cuenta) is None]
    resultado = None if any(cuenta in faltantes for cuenta in ("1", "2", "3")) else (
        saldos_base["1"] - saldos_base["2"] - saldos_base["3"]
    )
    utilidad_base = None if any(cuenta in faltantes for cuenta in ("5", "4")) else saldos_base["5"] - saldos_base["4"]
    diferencia = utilidad_base - resultado if utilidad_base is not None and resultado is not None else None
    return ValidacionUtilidad(
        estado="sin_datos" if diferencia is None else "coincide" if diferencia == 0 else "diferencia",
        utilidad_sin_neteo=utilidad_base, resultado_contable=resultado, diferencia=diferencia,
        ajuste_neteo=utilidad - utilidad_base if utilidad is not None and utilidad_base is not None else None,
        cuentas_sin_saldo=faltantes,
    )


class BalanceResultadosService:
    def __init__(self, repository):
        self.repository = repository

    def consultar(self, consulta: ConsultaBalanceResultados) -> ResumenBalanceResultados:
        id_contable = 1 if consulta.id_agencia == 0 else consulta.id_agencia
        agencia = self.repository.obtener_agencia(id_contable)
        if agencia is None:
            raise HTTPException(status_code=404, detail="Agencia no encontrada.")
        ajustes = {cuenta: MAPA_NETEO_CUENTAS[cuenta] for cuenta in CUENTAS
                   if consulta.neteo and cuenta in MAPA_NETEO_CUENTAS}
        codigos = tuple(dict.fromkeys((*CUENTAS, *ajustes.values(), *CUENTAS_VALIDACION)))
        saldos_base = self.repository.obtener_saldos(
            fecha_corte=consulta.fecha_corte, id_agencia=id_contable,
            id_empresa=agencia["id_empresa"], codigos_cuenta=codigos,
        )
        saldos = dict(saldos_base)
        for cuenta, ajuste in ajustes.items():
            if saldos.get(cuenta) is not None:
                saldos[cuenta] -= saldos_base.get(ajuste, Decimal("0.00"))
        indicadores = [calcular_indicador(item, saldos, consulta.neteo) for item in INDICADORES]
        return ResumenBalanceResultados(
            fecha_corte=consulta.fecha_corte, id_agencia=consulta.id_agencia,
            id_agencia_contable=id_contable, nombre_agencia=agencia["nombre"], neteo=consulta.neteo,
            cuentas_sin_saldo=[cuenta for cuenta in CUENTAS if saldos.get(cuenta) is None],
            indicadores=indicadores,
            margenes=[calcular_indicador(item, saldos, consulta.neteo) for item in MARGENES],
            validacion_utilidad=validar_utilidad(saldos_base, indicadores[-1]["saldo"]),
        )
