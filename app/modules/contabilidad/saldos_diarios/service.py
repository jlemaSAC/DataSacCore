from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.modules.contabilidad.repositories.sql_saldo_contable_repository import MAPA_NETEO_CUENTAS
from app.modules.contabilidad.saldos_diarios.schemas import ConsultaSaldosDiarios, SaldosDiariosResponse


def fecha_actual_ecuador() -> date:
    return datetime.now(ZoneInfo("America/Guayaquil")).date()


class SaldosDiariosService:
    def __init__(self, repository):
        self.repository = repository

    def consultar(self, consulta: ConsultaSaldosDiarios) -> SaldosDiariosResponse:
        fechas = [consulta.fecha_desde + timedelta(days=i) for i in range((consulta.fecha_hasta - consulta.fecha_desde).days + 1)]
        return self._consultar_fechas(consulta, fechas, mensual=False)

    def consultar_mensual(self, consulta: ConsultaSaldosDiarios) -> SaldosDiariosResponse:
        fechas: list[date] = []
        cursor = consulta.fecha_desde.replace(day=1)
        hoy = fecha_actual_ecuador()
        while cursor <= consulta.fecha_hasta:
            cierre = cursor.replace(day=monthrange(cursor.year, cursor.month)[1])
            fecha_consulta = hoy if cursor == hoy.replace(day=1) else cierre
            if consulta.fecha_desde <= fecha_consulta <= consulta.fecha_hasta and cursor <= hoy.replace(day=1):
                fechas.append(fecha_consulta)
            cursor = cierre + timedelta(days=1)
        return self._consultar_fechas(consulta, fechas, mensual=True)

    def _consultar_fechas(self, consulta: ConsultaSaldosDiarios, fechas: list[date], *, mensual: bool) -> SaldosDiariosResponse:
        id_contable = 1 if consulta.id_agencia == 0 else consulta.id_agencia
        empresa = self.repository.obtener_empresa_agencia(id_contable)
        if empresa is None:
            raise HTTPException(status_code=404, detail="Agencia no encontrada.")
        cuentas = self.repository.obtener_cuentas_activas(empresa)
        def consultar_saldos(desde: date, hasta: date):
            return self.repository.obtener_saldos(
                fecha_desde=desde, fecha_hasta=hasta,
                id_agencia=id_contable,
            )
        filas = (
            (row for fecha in fechas for row in consultar_saldos(fecha, fecha))
            if mensual else consultar_saldos(consulta.fecha_desde, consulta.fecha_hasta)
        )
        saldos = {(row["fecha"], row["codigo_cuenta"]): row["saldo"] for row in filas}
        datos = []
        for fecha in fechas:
            for cuenta in cuentas:
                codigo = cuenta["codigo_cuenta"]
                saldo = saldos.get((fecha, codigo))
                if saldo is None:
                    continue
                cuenta_neteada = MAPA_NETEO_CUENTAS.get(codigo) if consulta.neteo else None
                if cuenta_neteada:
                    saldo -= saldos.get((fecha, cuenta_neteada), Decimal("0"))
                datos.append({"fecha": fecha, **cuenta, "saldo": saldo})
        return SaldosDiariosResponse(
            fecha_desde=consulta.fecha_desde, fecha_hasta=consulta.fecha_hasta,
            id_agencia=consulta.id_agencia, id_agencia_contable=id_contable,
            neteo=consulta.neteo, total_registros=len(datos), datos=datos,
        )
