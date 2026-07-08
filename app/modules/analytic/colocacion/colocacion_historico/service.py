import calendar
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException

from app.modules.analytic.colocacion.colocacion_historico.domain import (
    ColocacionAgrupada,
    DimensionesColocacion,
)
from app.modules.analytic.colocacion.colocacion_historico.repositories.mongo_colocacion_historico_repository import (
    CorteMensual,
    MongoColocacionHistoricoRepository,
)
from app.modules.analytic.colocacion.colocacion_historico.repositories.sql_colocacion_historico_repository import (
    SqlColocacionHistoricoRepository,
)
from app.modules.analytic.colocacion.colocacion_historico.schemas import (
    ColocacionHistoricoAgrupacion,
    ColocacionHistoricoRangoResponse,
    InputColocacionHistoricoRango,
    InputSaldoInicialAgencia,
    ResumenMensualColocacion,
    ResumenRangoColocacion,
    SaldoInicialAgenciaResponse,
)
from app.modules.auth.schemas import AuthContext


logger = logging.getLogger("uvicorn.error")
MAX_MESES_RANGO = 60


@dataclass(frozen=True)
class SegmentoMensual:
    periodo: str
    anio: int
    mes: int
    fecha_desde: date
    fecha_hasta: date


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
            agrupaciones = self.mongo_repository.obtener_colocaciones_agrupadas(cortes)

            if input_data.anio == fecha_hoy.year:
                agrupaciones.extend(
                    self.sql_repository.obtener_colocaciones_agrupadas(
                        datetime.combine(fecha_hoy, time.min),
                        datetime.combine(fecha_hoy, time.max),
                    )
                )

            return self._construir_respuesta(
                input_data.anio,
                self._consolidar(agrupaciones),
            )
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

    def obtener_colocacion_historica_por_rango(
        self,
        input_data: InputColocacionHistoricoRango,
        auth_context: AuthContext,
    ) -> ColocacionHistoricoRangoResponse:
        try:
            fecha_sistema = auth_context.usuario.fecha_sistema
            fecha_hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
            if input_data.fecha_hasta > fecha_hoy:
                raise HTTPException(
                    status_code=400,
                    detail="fecha_hasta no puede ser posterior a la fecha del sistema.",
                )

            cantidad_meses = (
                (input_data.fecha_hasta.year - input_data.fecha_desde.year) * 12
                + input_data.fecha_hasta.month
                - input_data.fecha_desde.month
                + 1
            )
            if cantidad_meses > MAX_MESES_RANGO:
                raise HTTPException(
                    status_code=400,
                    detail=f"El rango no puede superar {MAX_MESES_RANGO} meses.",
                )

            segmentos = self._segmentar_rango(
                input_data.fecha_desde,
                input_data.fecha_hasta,
            )
            cortes: list[CorteMensual] = []
            for segmento in segmentos:
                fecha_fin_mongo = segmento.fecha_hasta
                if fecha_fin_mongo == fecha_hoy:
                    fecha_fin_mongo = fecha_hoy - timedelta(days=1)
                if fecha_fin_mongo < segmento.fecha_desde:
                    continue
                cortes.append(
                    CorteMensual(
                        anio=segmento.anio,
                        mes=segmento.mes,
                        fecha_corte=fecha_fin_mongo.strftime("%Y%m%d"),
                        fecha_inicio=datetime.combine(segmento.fecha_desde, time.min),
                        fecha_fin=datetime.combine(fecha_fin_mongo, time.max),
                    )
                )

            agrupaciones = self.mongo_repository.obtener_colocaciones_agrupadas(cortes)
            if input_data.fecha_desde <= fecha_hoy <= input_data.fecha_hasta:
                agrupaciones.extend(
                    self.sql_repository.obtener_colocaciones_agrupadas(
                        datetime.combine(fecha_hoy, time.min),
                        datetime.combine(fecha_hoy, time.max),
                    )
                )

            return self._construir_respuesta_rango(
                input_data=input_data,
                segmentos=segmentos,
                agrupaciones=self._consolidar(agrupaciones),
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "Error consultando colocacion historica entre %s y %s",
                input_data.fecha_desde,
                input_data.fecha_hasta,
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
                    anio=anio,
                    mes=mes,
                    fecha_corte=fecha_corte.strftime("%Y%m%d"),
                    fecha_inicio=inicio_mes,
                    fecha_fin=datetime.combine(fecha_corte, time.max),
                )
            )
        return cortes

    @staticmethod
    def _segmentar_rango(fecha_desde: date, fecha_hasta: date) -> list[SegmentoMensual]:
        segmentos: list[SegmentoMensual] = []
        cursor = date(fecha_desde.year, fecha_desde.month, 1)
        while cursor <= fecha_hasta:
            ultimo_dia = calendar.monthrange(cursor.year, cursor.month)[1]
            fin_mes = date(cursor.year, cursor.month, ultimo_dia)
            inicio_efectivo = max(fecha_desde, cursor)
            fin_efectivo = min(fecha_hasta, fin_mes)
            segmentos.append(
                SegmentoMensual(
                    periodo=f"{cursor.year:04d}-{cursor.month:02d}",
                    anio=cursor.year,
                    mes=cursor.month,
                    fecha_desde=inicio_efectivo,
                    fecha_hasta=fin_efectivo,
                )
            )
            cursor = (
                date(cursor.year + 1, 1, 1)
                if cursor.month == 12
                else date(cursor.year, cursor.month + 1, 1)
            )
        return segmentos

    @staticmethod
    def _consolidar(
        agrupaciones: list[ColocacionAgrupada],
    ) -> dict[DimensionesColocacion, ColocacionAgrupada]:
        consolidadas: dict[DimensionesColocacion, ColocacionAgrupada] = {}
        for agrupacion in agrupaciones:
            dimensiones = agrupacion.dimensiones
            actual = consolidadas.setdefault(
                dimensiones,
                ColocacionAgrupada(
                    dimensiones=dimensiones,
                    operaciones=0,
                    saldo_inicial=0.0,
                ),
            )
            actual.operaciones += agrupacion.operaciones
            actual.saldo_inicial += agrupacion.saldo_inicial
        return consolidadas

    @staticmethod
    def _construir_respuesta(
        anio: int,
        agrupaciones: dict[DimensionesColocacion, ColocacionAgrupada],
    ) -> SaldoInicialAgenciaResponse:
        operaciones_mes = {mes: 0 for mes in range(1, 13)}
        saldos_mes = {mes: 0.0 for mes in range(1, 13)}
        datos: list[ColocacionHistoricoAgrupacion] = []

        for dimensiones, agrupacion in sorted(agrupaciones.items()):
            operaciones_mes[dimensiones.mes] += agrupacion.operaciones
            saldos_mes[dimensiones.mes] += agrupacion.saldo_inicial
            datos.append(
                ColocacionHistoricoAgrupacion(
                    **dimensiones.__dict__,
                    operaciones=agrupacion.operaciones,
                    saldo_inicial=float(agrupacion.saldo_inicial),
                )
            )

        return SaldoInicialAgenciaResponse(
            anio=anio,
            total_operaciones=sum(operaciones_mes.values()),
            total_saldo_inicial=float(sum(saldos_mes.values())),
            resumen_mensual=[
                ResumenMensualColocacion(
                    periodo=f"{anio:04d}-{mes:02d}",
                    anio=anio,
                    mes=mes,
                    operaciones=operaciones_mes[mes],
                    saldo_inicial=float(saldos_mes[mes]),
                )
                for mes in range(1, 13)
            ],
            agrupaciones=datos,
        )

    @staticmethod
    def _construir_respuesta_rango(
        input_data: InputColocacionHistoricoRango,
        segmentos: list[SegmentoMensual],
        agrupaciones: dict[DimensionesColocacion, ColocacionAgrupada],
    ) -> ColocacionHistoricoRangoResponse:
        operaciones_periodo = {segmento.periodo: 0 for segmento in segmentos}
        saldos_periodo = {segmento.periodo: 0.0 for segmento in segmentos}
        datos: list[ColocacionHistoricoAgrupacion] = []

        for dimensiones, agrupacion in sorted(agrupaciones.items()):
            operaciones_periodo[dimensiones.periodo] += agrupacion.operaciones
            saldos_periodo[dimensiones.periodo] += agrupacion.saldo_inicial
            datos.append(
                ColocacionHistoricoAgrupacion(
                    **dimensiones.__dict__,
                    operaciones=agrupacion.operaciones,
                    saldo_inicial=float(agrupacion.saldo_inicial),
                )
            )

        return ColocacionHistoricoRangoResponse(
            fecha_desde=input_data.fecha_desde,
            fecha_hasta=input_data.fecha_hasta,
            total_operaciones=sum(operaciones_periodo.values()),
            total_saldo_inicial=float(sum(saldos_periodo.values())),
            resumen_mensual=[
                ResumenRangoColocacion(
                    periodo=segmento.periodo,
                    anio=segmento.anio,
                    mes=segmento.mes,
                    fecha_desde=segmento.fecha_desde,
                    fecha_hasta=segmento.fecha_hasta,
                    operaciones=operaciones_periodo[segmento.periodo],
                    saldo_inicial=float(saldos_periodo[segmento.periodo]),
                )
                for segmento in segmentos
            ],
            agrupaciones=datos,
        )
