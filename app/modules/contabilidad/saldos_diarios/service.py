from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException

from app.modules.contabilidad.repositories.sql_saldo_contable_repository import MAPA_NETEO_CUENTAS
from app.modules.contabilidad.saldos_diarios.schemas import ConsultaSaldosDiarios, SaldosDiariosResponse


class SaldosDiariosService:
    def __init__(self, repository):
        self.repository = repository

    def consultar(self, consulta: ConsultaSaldosDiarios) -> SaldosDiariosResponse:
        id_contable = 1 if consulta.id_agencia == 0 else consulta.id_agencia
        empresa = self.repository.obtener_empresa_agencia(id_contable)
        if empresa is None:
            raise HTTPException(status_code=404, detail="Agencia no encontrada.")
        cuentas = self.repository.obtener_cuentas_activas(empresa)
        saldos = {
            (row["fecha"], row["codigo_cuenta"]): row["saldo"]
            for row in self.repository.obtener_saldos(
                fecha_desde=consulta.fecha_desde, fecha_hasta=consulta.fecha_hasta,
                id_agencia=id_contable,
            )
        }
        datos = []
        fecha = consulta.fecha_desde
        while fecha <= consulta.fecha_hasta:
            for cuenta in cuentas:
                codigo = cuenta["codigo_cuenta"]
                saldo = saldos.get((fecha, codigo))
                if saldo is None:
                    continue
                cuenta_neteada = MAPA_NETEO_CUENTAS.get(codigo) if consulta.neteo else None
                if cuenta_neteada:
                    saldo -= saldos.get((fecha, cuenta_neteada), Decimal("0"))
                datos.append({"fecha": fecha, **cuenta, "saldo": saldo})
            fecha += timedelta(days=1)
        return SaldosDiariosResponse(
            fecha_desde=consulta.fecha_desde, fecha_hasta=consulta.fecha_hasta,
            id_agencia=consulta.id_agencia, id_agencia_contable=id_contable,
            neteo=consulta.neteo, total_registros=len(datos), datos=datos,
        )
