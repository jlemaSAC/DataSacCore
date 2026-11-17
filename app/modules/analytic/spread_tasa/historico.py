from calendar import monthrange
from collections.abc import Callable
from datetime import date, datetime, time
from decimal import Decimal

from fastapi import HTTPException

from app.modules.analytic.indicadores_financieros.fechas_historicas import construir_fechas_consulta_mensual
from .constants import CUENTAS_PROMEDIO, ZERO
from .historico_schemas import HistoricoSpreadInput
from .resumen_spread_tasa.service import fechas_promedio


def consultar_historico(
    repository, consulta: HistoricoSpreadInput, *, hoy: date, definiciones: dict,
    calcular_componentes: Callable[[dict, dict, int], dict], campo_tipo: str, campo_valor: str,
) -> dict:
    cortes = construir_fechas_consulta_mensual(
        periodo_desde=consulta.periodo_desde, periodo_hasta=consulta.periodo_hasta, hoy=hoy,
    )
    if len(cortes) > 60:
        raise HTTPException(400, 'El rango máximo permitido es de 60 meses.')
    ids = list(dict.fromkeys(0 if agencia == 1 else agencia for agencia in consulta.ids_agencia))
    fechas_por_corte = {corte: fechas_promedio(corte) for corte in cortes}
    fechas = sorted({fecha for grupo in fechas_por_corte.values() for fecha in grupo})
    cuentas_intereses = {cuenta for _, cuentas, _ in definiciones.values() for cuenta in cuentas}
    filas = repository.obtener_saldos(
        fechas=[datetime.combine(fecha, time.min) for fecha in fechas],
        ids_agencia=[1 if agencia == 0 else agencia for agencia in ids],
        codigos_cuenta=sorted(set(CUENTAS_PROMEDIO) | cuentas_intereses),
    )
    por_agencia = {}
    for fila in filas:
        fecha = fila['Fecha']
        if isinstance(fecha, datetime):
            fecha = fecha.date()
        por_agencia.setdefault(fila['IdAgencia'], {}).setdefault(fecha, {})[
            str(fila['CodigoCuenta']).strip()
        ] = Decimal(str(fila['SaldoFinal'] or 0))
    datos = []
    for corte in cortes:
        for agencia in ids:
            saldos_fechas = por_agencia.get(1 if agencia == 0 else agencia, {})
            # Mismo universo de cierres disponibles que el resumen, incluso si
            # una cuenta individual está ausente (su saldo en ese cierre es cero).
            historico = {
                fecha: saldos_fechas[fecha] for fecha in fechas_por_corte[corte]
                if fecha in saldos_fechas and any(c in saldos_fechas[fecha] for c in CUENTAS_PROMEDIO)
            }
            componentes = {}
            if corte in historico:
                cantidad = Decimal(len(historico))
                promedios = {
                    cuenta: sum((valores.get(cuenta, ZERO) for valores in historico.values()), ZERO) / cantidad
                    for cuenta in CUENTAS_PROMEDIO
                }
                componentes = calcular_componentes(saldos_fechas.get(corte, {}), promedios, corte.month)
            for indicador in definiciones:
                datos.append({
                    'periodo': corte.strftime('%Y-%m'), 'fecha_corte': corte,
                    'fecha_promedio_desde': fechas_por_corte[corte][0], 'id_agencia': agencia,
                    campo_tipo: indicador, 'cierres_con_datos': len(historico),
                    **componentes.get(indicador, {'intereses': None, 'saldo_promedio': None, campo_valor: None}),
                })
    return {'cortes': [{
        'periodo': corte.strftime('%Y-%m'), 'fecha_corte': corte,
        'parcial': corte == hoy and corte.day < monthrange(corte.year, corte.month)[1],
    } for corte in cortes], 'datos': datos}
