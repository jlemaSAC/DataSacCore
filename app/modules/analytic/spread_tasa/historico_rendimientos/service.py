from calendar import monthrange
from datetime import datetime, time
from decimal import Decimal

from fastapi import HTTPException

from app.modules.analytic.indicadores_financieros.fechas_historicas import construir_fechas_consulta_mensual, fecha_actual_ecuador
from app.modules.analytic.spread_tasa.calculos import PRODUCTOS_RENDIMIENTO, componentes_rendimientos
from app.modules.analytic.spread_tasa.constants import CUENTAS_PROMEDIO, ZERO
from app.modules.analytic.spread_tasa.resumen_spread_tasa.service import fechas_promedio
from .schemas import HistoricoRendimientosInput, HistoricoRendimientosResponse


class HistoricoRendimientosService:
    def __init__(self, repository):
        self.repository = repository

    def consultar(self, consulta: HistoricoRendimientosInput) -> HistoricoRendimientosResponse:
        hoy = fecha_actual_ecuador()
        cortes = construir_fechas_consulta_mensual(
            periodo_desde=consulta.periodo_desde, periodo_hasta=consulta.periodo_hasta, hoy=hoy)
        if len(cortes) > 60:
            raise HTTPException(400, 'El rango máximo permitido es de 60 meses.')
        if cortes[0].year == 1:
            raise HTTPException(400, 'Se requiere el cierre del año anterior.')
        ids = list(dict.fromkeys(0 if id_agencia == 1 else id_agencia for id_agencia in consulta.ids_agencia))
        fechas_por_corte = {corte: fechas_promedio(corte) for corte in cortes}
        fechas = sorted({fecha for grupo in fechas_por_corte.values() for fecha in grupo})
        cuentas_intereses = {c for _, cuentas, _ in PRODUCTOS_RENDIMIENTO.values() for c in cuentas}
        filas = self.repository.obtener_saldos(
            fechas=[datetime.combine(fecha, time.min) for fecha in fechas],
            ids_agencia=[1 if id_agencia == 0 else id_agencia for id_agencia in ids],
            codigos_cuenta=sorted(set(CUENTAS_PROMEDIO) | cuentas_intereses))
        por_agencia = {}
        for fila in filas:
            fecha = fila['Fecha']
            if isinstance(fecha, datetime):
                fecha = fecha.date()
            por_agencia.setdefault(fila['IdAgencia'], {}).setdefault(fecha, {})[str(fila['CodigoCuenta']).strip()] = Decimal(str(fila['SaldoFinal'] or 0))
        datos = []
        for corte in cortes:
            for id_agencia in ids:
                saldos_fechas = por_agencia.get(1 if id_agencia == 0 else id_agencia, {})
                historico = {fecha: saldos_fechas[fecha] for fecha in fechas_por_corte[corte]
                             if fecha in saldos_fechas and any(c in saldos_fechas[fecha] for c in CUENTAS_PROMEDIO)}
                componentes = {}
                if corte in historico:
                    cantidad = Decimal(len(historico))
                    promedios = {c: sum((valores.get(c, ZERO) for valores in historico.values()), ZERO) / cantidad for c in CUENTAS_PROMEDIO}
                    componentes = componentes_rendimientos(saldos_fechas.get(corte, {}), promedios, corte.month)
                for producto in PRODUCTOS_RENDIMIENTO:
                    datos.append({
                        'periodo': corte.strftime('%Y-%m'), 'fecha_corte': corte,
                        'fecha_promedio_desde': fechas_por_corte[corte][0], 'id_agencia': id_agencia,
                        'producto': producto, 'cierres_con_datos': len(historico),
                        **componentes.get(producto, {'intereses': None, 'saldo_promedio': None, 'rendimiento': None}),
                    })
        return HistoricoRendimientosResponse(cortes=[{
            'periodo': corte.strftime('%Y-%m'), 'fecha_corte': corte,
            'parcial': corte == hoy and corte.day < monthrange(corte.year, corte.month)[1],
        } for corte in cortes], datos=datos)
