from calendar import monthrange
from datetime import date, datetime, time
from decimal import Decimal

from fastapi import HTTPException

from app.modules.analytic.spread_tasa.resumen_spread_tasa.schemas import ResumenSpreadTasaResponse, SpreadAgenciasResponse


from app.modules.analytic.spread_tasa.constants import (
    INTERESES_CARTERA, CUENTAS_CORTE, MICROCREDITO_POR_VENCER, CARTERA_POR_VENCER,
    FUENTES_FONDEO, CUENTAS_PROMEDIO, ZERO,
)
from app.modules.analytic.spread_tasa.calculos import componentes_costos, componentes_rendimientos, componentes_spread


def fechas_promedio(fecha_corte: date) -> list[date]:
    fechas = [date(fecha_corte.year - 1, 12, 31)]
    for mes in range(1, fecha_corte.month + 1):
        cierre = date(fecha_corte.year, mes, monthrange(fecha_corte.year, mes)[1])
        if cierre <= fecha_corte:
            fechas.append(cierre)
    if fechas[-1] != fecha_corte:
        fechas.append(fecha_corte)
    return fechas


def calcular_spread(saldos: dict[str, Decimal], promedios: dict[str, Decimal], mes: int):
    componentes = componentes_spread(saldos, promedios, mes)
    return (componentes['rendimiento_cartera_por_vencer']['valor'],
            componentes['costo_promedio_fondeo']['valor'], componentes['spread_tasa']['valor'])


class ResumenSpreadTasaService:
    def __init__(self, repository, agencias_repository=None):
        self.repository = repository
        self.agencias_repository = agencias_repository

    def consultar(self, fecha_corte: date, id_agencia: int = 0) -> ResumenSpreadTasaResponse:
        id_agencia_contable = 1 if id_agencia == 0 else id_agencia
        fechas = fechas_promedio(fecha_corte)
        desde = fechas[0]
        corte = self.repository.get_saldos_contables_con_neteo(
            fecha=datetime.combine(fecha_corte, time.min), id_agencia=id_agencia_contable,
            codigos_cuenta=CUENTAS_CORTE, neteo=1, preservar_decimal=True,
        )
        diario = self.repository.get_saldos_contables_fechas_con_neteo(
            fechas=[datetime.combine(fecha, time.min) for fecha in fechas], id_agencia=id_agencia_contable,
            codigos_cuenta=CUENTAS_PROMEDIO, neteo=1, preservar_decimal=True,
        )
        if not diario:
            raise HTTPException(status_code=404, detail="No existen saldos contables para la fecha de corte o el periodo.")
        saldos = {str(row["CodigoCuenta"]).strip(): Decimal(str(row["SaldoFinal"] or 0)) for row in corte}
        por_fecha = {}
        for row in diario:
            fecha = row["Fecha"]
            if isinstance(fecha, datetime):
                fecha = fecha.date()
            codigo = str(row["CodigoCuenta"]).strip()
            por_fecha.setdefault(fecha, {})[codigo] = Decimal(str(row["SaldoFinal"] or 0))
        # Se promedian los cierres disponibles y la fecha de corte seleccionada.
        # Una cuenta ausente en una fecha con registros se considera cero.
        if fecha_corte not in por_fecha:
            raise HTTPException(status_code=404, detail="No existen saldos promedio en la fecha de corte.")
        cantidad = Decimal(len(por_fecha))
        promedios = {codigo: sum((dia.get(codigo, ZERO) for dia in por_fecha.values()), ZERO) / cantidad for codigo in CUENTAS_PROMEDIO}
        cartera_vencer = sum((promedios[c] for c in CARTERA_POR_VENCER), ZERO)

        promedio_fondeo = sum((promedios[c] for c in FUENTES_FONDEO), ZERO)
        rendimiento, costo_fondeo, spread = calcular_spread(saldos, promedios, fecha_corte.month)
        rendimientos = componentes_rendimientos(saldos, promedios, fecha_corte.month)
        costos = componentes_costos(saldos, promedios, fecha_corte.month)
        indicadores = {
            "costo_ahorro_plazo": costos['ahorro_plazo']['costo'],
            "costo_ahorro_vista": costos['ahorro_vista']['costo'],
            "costo_obligaciones_financieras": costos['obligaciones_financieras']['costo'],
            "costo_promedio_fondeo": costo_fondeo,
            "spread_tasa": spread,
            "rendimiento_microcredito_por_vencer": rendimientos['microcredito']['rendimiento'],
            "rendimiento_credito_consumo_por_vencer": rendimientos['consumo']['rendimiento'],
            "rendimiento_cartera_por_vencer": rendimientos['cartera']['rendimiento'],
            "inmobiliario_por_vencer": rendimientos['inmobiliario']['rendimiento'],
        }
        return ResumenSpreadTasaResponse(
            fecha_corte=fecha_corte, fecha_promedio_desde=desde, id_agencia=id_agencia,
            id_agencia_contable=id_agencia_contable,
            meses=fecha_corte.month, dias_con_datos=len(por_fecha), indicadores=indicadores,
            saldos_corte={c: saldos.get(c, ZERO) for c in CUENTAS_CORTE},
            saldos_promedio={**promedios, "cartera_por_vencer": cartera_vencer, "fuentes_fondeo": promedio_fondeo},
            costo_fuentes_fondeo_spread=costo_fondeo,
        )

    def consultar_agencias(self, fecha_corte: date, ids_agencia: list[int]) -> SpreadAgenciasResponse:
        ids = list(dict.fromkeys(ids_agencia))
        filas = self.agencias_repository.obtener_saldos(
            fechas=[datetime.combine(fecha, time.min) for fecha in fechas_promedio(fecha_corte)],
            ids_agencia=ids,
            codigos_cuenta=list(dict.fromkeys((*CUENTAS_CORTE, *CUENTAS_PROMEDIO))),
        )
        por_agencia = {id_agencia: {} for id_agencia in ids}
        for fila in filas:
            id_agencia = fila['IdAgencia']
            if id_agencia not in por_agencia:
                continue
            fecha = fila['Fecha']
            if isinstance(fecha, datetime):
                fecha = fecha.date()
            codigo = str(fila['CodigoCuenta']).strip()
            por_agencia[id_agencia].setdefault(fecha, {})[codigo] = Decimal(str(fila['SaldoFinal'] or 0))
        resultados = []
        for id_agencia, fechas in por_agencia.items():
            # Igual que el resumen individual: solo fechas con saldos de cuentas de promedio.
            historico = {fecha: valores for fecha, valores in fechas.items()
                         if any(codigo in valores for codigo in CUENTAS_PROMEDIO)}
            rendimiento = costo = spread = None
            if fecha_corte in historico:
                cantidad = Decimal(len(historico))
                promedios = {codigo: sum((valores.get(codigo, ZERO) for valores in historico.values()), ZERO) / cantidad
                             for codigo in CUENTAS_PROMEDIO}
                rendimiento, costo, spread = calcular_spread(fechas.get(fecha_corte, {}), promedios, fecha_corte.month)
            resultados.append({'id_agencia': id_agencia, 'rendimiento_cartera_por_vencer': rendimiento,
                               'costo_promedio_fondeo': costo, 'spread_tasa': spread})
        return SpreadAgenciasResponse(fecha_corte=fecha_corte, agencias=resultados)
