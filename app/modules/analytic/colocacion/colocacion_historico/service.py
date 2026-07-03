import calendar
import logging
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException

from app.modules.analytic.colocacion.colocacion_historico.repositories.mongo_colocacion_historico_repository import (
    CorteMensual,
    MongoColocacionHistoricoRepository,
)
from app.modules.analytic.colocacion.colocacion_historico.repositories.sql_colocacion_historico_repository import (
    SqlColocacionHistoricoRepository,
)
from app.modules.analytic.colocacion.colocacion_historico.schemas import (
    InputSaldoInicialAgencia,
    SaldoInicialAgenciaDetalle,
    SaldoInicialAgenciaResponse,
    SaldoInicialMes,
)
from app.modules.auth.schemas import AuthContext


logger = logging.getLogger("uvicorn.error")


class ColocacionHistoricoService:
    def __init__(
        self,
        mongo_repository: MongoColocacionHistoricoRepository,
        sql_repository: SqlColocacionHistoricoRepository,
    ) -> None:
        self.mongo_repository = mongo_repository
        self.sql_repository = sql_repository

    def obtener_saldo_inicial_agencias_por_mes(
        self,
        input_data: InputSaldoInicialAgencia,
        auth_context: AuthContext,
    ) -> SaldoInicialAgenciaResponse:
        try:
            fecha_sistema = auth_context.usuario.fecha_sistema
            fecha_hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
            cortes = self._construir_cortes(input_data.anio, fecha_hoy)
            saldos_por_mes = self.mongo_repository.obtener_saldos_iniciales_por_cortes(cortes)

            if input_data.anio == fecha_hoy.year:
                saldos_hoy = self.sql_repository.obtener_saldos_adjudicados_por_agencia(
                    datetime.combine(fecha_hoy, time.min),
                    datetime.combine(fecha_hoy, time.max),
                )
                saldos_mes_actual = saldos_por_mes.setdefault(fecha_hoy.month, {})
                for agencia, saldo in saldos_hoy.items():
                    saldos_mes_actual[agencia] = saldos_mes_actual.get(agencia, 0.0) + saldo

            return self._construir_respuesta(input_data.anio, saldos_por_mes)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "Error consultando colocacion historica para el anio %s",
                input_data.anio,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error consultando colocacion historica: {exc}",
            ) from exc

    @staticmethod
    def _construir_cortes(anio: int, fecha_hoy: date) -> list[CorteMensual]:
        if anio > fecha_hoy.year:
            return []

        ultimo_mes = fecha_hoy.month if anio == fecha_hoy.year else 12
        cortes: list[CorteMensual] = []
        for mes in range(1, ultimo_mes + 1):
            inicio_mes = datetime(anio, mes, 1)
            ultimo_dia = calendar.monthrange(anio, mes)[1]
            fin_mes = datetime(anio, mes, ultimo_dia, 23, 59, 59)
            fecha_corte = fin_mes.date()

            if anio == fecha_hoy.year and mes == fecha_hoy.month:
                fecha_corte = fecha_hoy - timedelta(days=1)
            if fecha_corte < inicio_mes.date():
                continue

            cortes.append(
                CorteMensual(
                    mes=mes,
                    fecha_corte=fecha_corte.strftime("%Y%m%d"),
                    fecha_inicio=inicio_mes,
                    fecha_fin=datetime.combine(fecha_corte, time.max),
                )
            )
        return cortes

    @staticmethod
    def _construir_respuesta(
        anio: int,
        saldos_por_mes: dict[int, dict[str, float]],
    ) -> SaldoInicialAgenciaResponse:
        agencias = sorted(
            {
                agencia
                for saldos_mes in saldos_por_mes.values()
                for agencia in saldos_mes
            }
        )
        return SaldoInicialAgenciaResponse(
            anio=anio,
            agencias=[
                SaldoInicialAgenciaDetalle(
                    agencia=agencia,
                    meses=[
                        SaldoInicialMes(
                            mes=mes,
                            saldo_inicial=float(saldos_por_mes.get(mes, {}).get(agencia, 0.0)),
                        )
                        for mes in range(1, 13)
                    ],
                )
                for agencia in agencias
            ],
        )
