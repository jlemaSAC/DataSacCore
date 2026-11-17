from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from fastapi import HTTPException
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.service import CUENTAS
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.schemas import VariacionResponse
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import MAPA_NETEO_CUENTAS


def fecha_anterior(fecha, tipo):
    indice = fecha.year * 12 + fecha.month - 1 - (12 if tipo == 'anual' else 1)
    anio, mes = divmod(indice, 12)
    return date(anio, mes + 1, min(fecha.day, monthrange(anio, mes + 1)[1]))


class VariacionBalanceService:
    def __init__(self, repository):
        self.repository = repository

    def consultar(self, consulta):
        agencia_id = 1 if consulta.id_agencia == 0 else consulta.id_agencia
        agencia = self.repository.obtener_agencia(agencia_id)
        if agencia is None:
            raise HTTPException(status_code=404, detail='Agencia no encontrada.')
        if consulta.tipo in ('mensual_cortes', 'anual_meses'):
            fechas = []
            mes = consulta.fecha_desde.replace(day=1)
            while mes <= consulta.fecha_hasta:
                fechas.append(mes.replace(day=min(consulta.fecha_hasta.day, monthrange(mes.year, mes.month)[1])))
                mes = mes.replace(day=monthrange(mes.year, mes.month)[1]) + timedelta(days=1)
        elif consulta.dia_mes is None:
            fechas = [consulta.fecha_desde + timedelta(days=i) for i in range((consulta.fecha_hasta - consulta.fecha_desde).days + 1)]
        else:
            fechas = []
            mes = consulta.fecha_desde.replace(day=1)
            while mes <= consulta.fecha_hasta:
                dia = min(consulta.dia_mes, monthrange(mes.year, mes.month)[1])
                corte = mes.replace(day=dia)
                if consulta.fecha_desde <= corte <= consulta.fecha_hasta:
                    fechas.append(corte)
                mes = mes.replace(day=monthrange(mes.year, mes.month)[1]) + timedelta(days=1)
        if consulta.tipo in ('mensual_cortes', 'anual_meses'):
            comparaciones = []
            for fecha in fechas:
                indice = fecha.year * 12 + fecha.month - 1 - (12 if consulta.tipo == 'anual_meses' else 1)
                anio, mes_cero = divmod(indice, 12)
                comparaciones.append(date(anio, mes_cero + 1, min(consulta.fecha_hasta.day, monthrange(anio, mes_cero + 1)[1])))
        else:
            comparaciones = [fecha_anterior(fecha, consulta.tipo) for fecha in fechas]
        fechas_consulta = sorted(set(fechas + comparaciones))
        ajustes = {codigo: MAPA_NETEO_CUENTAS[codigo] for codigo, _ in CUENTAS if consulta.neteo and codigo in MAPA_NETEO_CUENTAS}
        codigos = tuple(dict.fromkeys([codigo for codigo, _ in CUENTAS] + list(ajustes.values())))
        saldos = {}
        # SQL Server limita los parámetros por sentencia; distribuir los cortes en lotes.
        for inicio in range(0, len(fechas_consulta), 500):
            filas = self.repository.obtener_saldos_fechas(fechas=fechas_consulta[inicio:inicio + 500], id_agencia=agencia_id, id_empresa=agencia['id_empresa'], codigos_cuenta=codigos)
            saldos.update({(fila['fecha'], fila['codigo_cuenta']): fila['saldo'] for fila in filas})
        datos = []
        for fecha, anterior in zip(fechas, comparaciones):
            corte = dict(fecha=fecha, fecha_comparacion=anterior, cuentas_sin_saldo=[])
            for codigo, nombre in CUENTAS:
                actual, previo = saldos.get((fecha, codigo)), saldos.get((anterior, codigo))
                if actual is None or previo is None:
                    corte['cuentas_sin_saldo'].append(codigo)
                    corte[nombre] = None
                    continue
                if codigo in ajustes:
                    actual -= saldos.get((fecha, ajustes[codigo]), Decimal('0'))
                    previo -= saldos.get((anterior, ajustes[codigo]), Decimal('0'))
                corte[nombre] = actual - previo
            datos.append(corte)
        return VariacionResponse(**consulta.model_dump(), id_agencia_contable=agencia_id, nombre_agencia=agencia['nombre'], datos=datos)
