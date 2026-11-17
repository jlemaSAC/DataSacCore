from calendar import monthrange
from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException

from app.modules.analytic.evolucion_cuentas.evolucion_balance_general import schemas
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.schemas import (
    ConsultaEvolucionBalance,
    EvolucionBalanceResponse,
)
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import MAPA_NETEO_CUENTAS

CUENTAS = (("1", "activos"), ("2", "pasivos"), ("3", "patrimonio"))


class IndicadoresBalance:
    cuentas = CUENTAS

    @property
    def indicadores(self):
        return self.cuentas

    def valores_corte(self, saldos, fecha, ajustes):
        valores = {}
        for codigo, campo in self.cuentas:
            saldo = saldos.get((fecha, codigo))
            if saldo is not None and codigo in ajustes:
                saldo -= saldos.get((fecha, ajustes[codigo]), Decimal("0.00"))
            valores[campo] = saldo
        return valores

    def completar_corte(self, corte: dict) -> None:
        pass


class EvolucionBalanceService(IndicadoresBalance):
    response_model = EvolucionBalanceResponse

    def __init__(self, repository):
        self.repository = repository

    def consultar(self, consulta: ConsultaEvolucionBalance):
        id_contable = 1 if consulta.id_agencia == 0 else consulta.id_agencia
        agencia = self.repository.obtener_agencia(id_contable)
        if agencia is None:
            raise HTTPException(status_code=404, detail="Agencia no encontrada.")
        fechas = []
        hoy = schemas.fecha_actual_ecuador()
        cursor = consulta.fecha_desde
        while cursor <= consulta.fecha_hasta:
            if consulta.frecuencia == "mensual":
                cierre = cursor.replace(day=monthrange(cursor.year, cursor.month)[1])
                corte = min(cierre, hoy) if cursor.replace(day=1) == hoy.replace(day=1) else cierre
                if cursor <= corte <= consulta.fecha_hasta:
                    fechas.append(corte)
                cursor = cierre + timedelta(days=1)
            else:
                fechas.append(cursor)
                cursor += timedelta(days=1)
        if not fechas:
            raise HTTPException(status_code=422, detail="El rango no contiene ningún fin de mes ni el corte del día actual.")
        ajustes = {codigo: MAPA_NETEO_CUENTAS[codigo] for codigo, _ in self.cuentas
                   if consulta.neteo and codigo in MAPA_NETEO_CUENTAS}
        codigos = tuple(dict.fromkeys([codigo for codigo, _ in self.cuentas] + list(ajustes.values())))
        filas = self.repository.obtener_saldos_fechas(
            fechas=fechas, id_agencia=id_contable, id_empresa=agencia["id_empresa"], codigos_cuenta=codigos,
        )
        saldos = {(row["fecha"], row["codigo_cuenta"]): row["saldo"] for row in filas}
        datos = []
        for fecha in fechas:
            corte = {
                "fecha": fecha,
                "parcial": consulta.frecuencia == "mensual" and fecha.day < monthrange(fecha.year, fecha.month)[1],
            }
            valores = self.valores_corte(saldos, fecha, ajustes)
            corte.update(valores)
            corte["cuentas_sin_saldo"] = [
                codigo for codigo, campo in self.indicadores if valores[campo] is None
            ]
            self.completar_corte(corte)
            datos.append(corte)
        return self.response_model(
            **consulta.model_dump(), id_agencia_contable=id_contable,
            nombre_agencia=agencia["nombre"], datos=datos,
        )
