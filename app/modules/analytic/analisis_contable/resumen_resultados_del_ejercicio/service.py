from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.modules.contabilidad.repositories.sql_saldo_contable_repository import MAPA_NETEO_CUENTAS
from app.modules.analytic.analisis_contable.calculos_resultados import calcular_indicador
from app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.domain import CUENTAS, FILAS
from app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.schemas import (
    ConsultaCorteResultados, ConsultaHistoricoResultados, ConsultaHistoricoMensualResultados, ResultadosEjercicioResponse,
)


def fecha_actual_ecuador() -> date:
    return datetime.now(ZoneInfo("America/Guayaquil")).date()


class ResultadosEjercicioService:
    def __init__(self, repository):
        self.repository = repository

    def consultar_corte(self, consulta: ConsultaCorteResultados) -> ResultadosEjercicioResponse:
        return self._consultar(consulta, [consulta.fecha_corte], consulta.fecha_corte, consulta.fecha_corte)

    def consultar_diario(self, consulta: ConsultaHistoricoResultados) -> ResultadosEjercicioResponse:
        fechas = [consulta.fecha_desde + timedelta(days=i)
                  for i in range((consulta.fecha_hasta - consulta.fecha_desde).days + 1)]
        return self._consultar(consulta, fechas, consulta.fecha_desde, consulta.fecha_hasta)

    def consultar_mensual(self, consulta: ConsultaHistoricoMensualResultados) -> ResultadosEjercicioResponse:
        fechas = []
        hoy = fecha_actual_ecuador()
        cursor = consulta.fecha_desde.replace(day=1)
        while cursor <= consulta.fecha_hasta:
            cierre = cursor.replace(day=monthrange(cursor.year, cursor.month)[1])
            fecha = hoy if cursor == hoy.replace(day=1) else cierre
            if consulta.fecha_desde <= fecha <= consulta.fecha_hasta and cursor <= hoy.replace(day=1):
                fechas.append(fecha)
            if cierre >= consulta.fecha_hasta:
                break
            cursor = cierre + timedelta(days=1)
        return self._consultar(consulta, fechas, consulta.fecha_desde, consulta.fecha_hasta)

    def _consultar(self, consulta, fechas: list[date], desde: date, hasta: date) -> ResultadosEjercicioResponse:
        id_contable = 1 if consulta.id_agencia == 0 else consulta.id_agencia
        agencia = self.repository.obtener_agencia(id_contable)
        if agencia is None:
            raise HTTPException(status_code=404, detail="Agencia no encontrada.")
        ajustes = {cuenta: MAPA_NETEO_CUENTAS[cuenta] for cuenta in CUENTAS
                   if consulta.neteo and cuenta in MAPA_NETEO_CUENTAS}
        codigos = tuple(dict.fromkeys((*CUENTAS, *ajustes.values())))
        rows = self.repository.obtener_saldos_fechas(
            fechas=fechas, id_agencia=id_contable, id_empresa=agencia["id_empresa"], codigos_cuenta=codigos,
        ) if fechas else []
        por_fecha = {fecha: {} for fecha in fechas}
        for row in rows:
            if row["fecha"] in por_fecha:
                por_fecha[row["fecha"]][row["codigo_cuenta"]] = row["saldo"]
        filas = []
        for codigo, cuenta, signo, nombre, terminos in FILAS:
            indicador = calcular_indicador((codigo, nombre, terminos), {}, consulta.neteo)
            filas.append(dict(codigo=codigo, cuenta=cuenta, signo=signo, nombre=nombre,
                              es_resultado=cuenta is None, formula=indicador["formula"]))
        datos = []
        for fecha, base in por_fecha.items():
            saldos = dict(base)
            for cuenta, ajuste in ajustes.items():
                if saldos.get(cuenta) is not None:
                    saldos[cuenta] -= base.get(ajuste, Decimal("0.00"))
            for codigo, _, _, nombre, terminos in FILAS:
                indicador = calcular_indicador((codigo, nombre, terminos), saldos, consulta.neteo)
                datos.append(dict(fecha=fecha, codigo_fila=codigo, saldo=indicador["saldo"]))
        return ResultadosEjercicioResponse(
            fecha_desde=desde, fecha_hasta=hasta, id_agencia=consulta.id_agencia,
            id_agencia_contable=id_contable, nombre_agencia=agencia["nombre"], neteo=consulta.neteo,
            fechas=fechas, filas=filas, datos=datos, total_registros=len(datos),
        )
