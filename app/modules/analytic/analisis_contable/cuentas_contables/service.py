from decimal import Decimal

from fastapi import HTTPException

from app.modules.contabilidad.repositories.sql_saldo_contable_repository import MAPA_NETEO_CUENTAS

from app.modules.analytic.analisis_contable.cuentas_contables.schemas import (
    ConsultaCuentasContables,
    ResumenCuentasContables,
)


# Cada término es (cuenta, coeficiente). Se usan saldos con su signo contable;
# 1499 puede ser negativo y se resta tal como establece la fórmula de cartera bruta.
INDICADORES = (
    ("activos", "Activos", "1", (("1", 1),)),
    ("cartera_bruta", "Cartera Bruta", "14 - 1499", (("14", 1), ("1499", -1))),
    ("cartera_neta", "Cartera Neta", "14", (("14", 1),)),
    ("inversiones", "Inversiones", "13", (("13", 1),)),
    ("pasivos", "Pasivos", "2", (("2", 1),)),
    ("depositos_vista", "Depósitos a la Vista", "2101", (("2101", 1),)),
    ("depositos_plazo", "Depósitos a Plazo", "2103", (("2103", 1),)),
    ("patrimonio", "Patrimonio", "3", (("3", 1),)),
    ("capital_social", "Capital Social", "31", (("31", 1),)),
    ("reservas", "Reservas", "33", (("33", 1),)),
)
CUENTAS = tuple(dict.fromkeys(cuenta for *_, terminos in INDICADORES for cuenta, _ in terminos))


class CuentasContablesService:
    def __init__(self, repository):
        self.repository = repository

    def consultar(self, consulta: ConsultaCuentasContables) -> ResumenCuentasContables:
        id_contable = 1 if consulta.id_agencia == 0 else consulta.id_agencia
        agencia = self.repository.obtener_agencia(id_contable)
        if agencia is None:
            raise HTTPException(status_code=404, detail="Agencia no encontrada.")
        cuentas_neteadas = {
            cuenta: MAPA_NETEO_CUENTAS[cuenta]
            for cuenta in CUENTAS if consulta.neteo and cuenta in MAPA_NETEO_CUENTAS
        }
        codigos_consulta = tuple(dict.fromkeys((*CUENTAS, *cuentas_neteadas.values())))
        saldos_base = self.repository.obtener_saldos(
            fecha_corte=consulta.fecha_corte, id_agencia=id_contable,
            id_empresa=agencia["id_empresa"], codigos_cuenta=codigos_consulta,
        )
        saldos = dict(saldos_base)
        for cuenta, ajuste in cuentas_neteadas.items():
            if saldos.get(cuenta) is not None:
                # Igual que saldos diarios: un ajuste sin registro se considera cero.
                saldos[cuenta] -= saldos_base.get(ajuste, Decimal("0.00"))
        faltantes = [cuenta for cuenta in CUENTAS if saldos.get(cuenta) is None]
        indicadores = []
        for codigo, nombre, formula, terminos in INDICADORES:
            if formula in cuentas_neteadas:
                formula = f"{formula} - {cuentas_neteadas[formula]}"
            saldo = None if any(cuenta in faltantes for cuenta, _ in terminos) else sum(
                (saldos[cuenta] * coeficiente for cuenta, coeficiente in terminos), Decimal("0.00")
            )
            indicadores.append(dict(codigo=codigo, nombre=nombre, formula=formula, saldo=saldo))
        return ResumenCuentasContables(
            fecha_corte=consulta.fecha_corte, id_agencia=consulta.id_agencia,
            id_agencia_contable=id_contable, nombre_agencia=agencia["nombre"],
            neteo=consulta.neteo,
            cuentas_sin_saldo=faltantes, indicadores=indicadores,
        )
