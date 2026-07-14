import calendar
import logging
from dataclasses import dataclass
from datetime import date, datetime
from time import perf_counter

from fastapi import HTTPException

from app.modules.analytic.recuperacion.recuperacion_historico.domain import RecuperacionAgrupada
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.mongo_recuperacion_historico_repository import (
    MongoRecuperacionHistoricoRepository,
)
from app.modules.analytic.recuperacion.recuperacion_historico.schemas import (
    InputRecuperacionHistoricoRango,
    RecuperacionHistoricoAgrupacion,
    RecuperacionHistoricoRangoResponse,
    ResumenMensualRecuperacion,
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


class RecuperacionHistoricoService:
    def __init__(self, mongo_repository: MongoRecuperacionHistoricoRepository) -> None:
        self.mongo_repository = mongo_repository

    def obtener_recuperacion_por_rango(
        self,
        input_data: InputRecuperacionHistoricoRango,
        auth_context: AuthContext,
    ) -> RecuperacionHistoricoRangoResponse:
        try:
            fecha_sistema = auth_context.usuario.fecha_sistema
            fecha_hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
            if input_data.fecha_hasta > fecha_hoy:
                raise HTTPException(400, "fecha_hasta no puede ser posterior a la fecha del sistema.")
            cantidad_meses = (
                (input_data.fecha_hasta.year - input_data.fecha_desde.year) * 12
                + input_data.fecha_hasta.month - input_data.fecha_desde.month + 1
            )
            if cantidad_meses > MAX_MESES_RANGO:
                raise HTTPException(400, f"El rango no puede superar {MAX_MESES_RANGO} meses.")

            inicio_mongo = perf_counter()
            agrupaciones = self.mongo_repository.obtener_recuperaciones_agrupadas(input_data)
            print(
                "[recuperacion][service] mongo_total_ms="
                f"{(perf_counter() - inicio_mongo) * 1000:.2f}"
            )
            inicio_respuesta = perf_counter()
            respuesta = self._construir_respuesta(input_data, agrupaciones)
            print(
                "[recuperacion][service] respuesta_ms="
                f"{(perf_counter() - inicio_respuesta) * 1000:.2f} "
                f"agrupaciones={len(respuesta.agrupaciones)}"
            )
            return respuesta
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "Error consultando recuperacion Mongo entre %s y %s",
                input_data.fecha_desde,
                input_data.fecha_hasta,
            )
            raise HTTPException(status_code=500, detail=f"Error consultando recuperacion: {exc}") from exc

    @staticmethod
    def _segmentos(fecha_desde: date, fecha_hasta: date) -> list[SegmentoMensual]:
        segmentos: list[SegmentoMensual] = []
        cursor = date(fecha_desde.year, fecha_desde.month, 1)
        while cursor <= fecha_hasta:
            fin_mes = date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1])
            segmentos.append(SegmentoMensual(
                periodo=f"{cursor.year:04d}-{cursor.month:02d}",
                anio=cursor.year,
                mes=cursor.month,
                fecha_desde=max(cursor, fecha_desde),
                fecha_hasta=min(fin_mes, fecha_hasta),
            ))
            cursor = date(cursor.year + 1, 1, 1) if cursor.month == 12 else date(cursor.year, cursor.month + 1, 1)
        return segmentos

    def _construir_respuesta(
        self,
        input_data: InputRecuperacionHistoricoRango,
        agrupaciones: list[RecuperacionAgrupada],
    ) -> RecuperacionHistoricoRangoResponse:
        segmentos = self._segmentos(input_data.fecha_desde, input_data.fecha_hasta)
        totales_periodo = {segmento.periodo: 0.0 for segmento in segmentos}
        datos: list[RecuperacionHistoricoAgrupacion] = []
        for agrupacion in sorted(
            agrupaciones,
            key=lambda item: (item.periodo, *(str(valor or "") for valor in item.dimensiones.values())),
        ):
            totales_periodo[agrupacion.periodo] = totales_periodo.get(agrupacion.periodo, 0.0) + agrupacion.total_recuperado
            datos.append(RecuperacionHistoricoAgrupacion(
                periodo=agrupacion.periodo,
                anio=agrupacion.anio,
                mes=agrupacion.mes,
                **agrupacion.dimensiones,
                total_recuperado=agrupacion.total_recuperado,
            ))
        return RecuperacionHistoricoRangoResponse(
            fecha_desde=input_data.fecha_desde,
            fecha_hasta=input_data.fecha_hasta,
            total_recuperado=float(sum(totales_periodo.values())),
            resumen_mensual=[
                ResumenMensualRecuperacion(
                    periodo=segmento.periodo,
                    anio=segmento.anio,
                    mes=segmento.mes,
                    fecha_desde=segmento.fecha_desde,
                    fecha_hasta=segmento.fecha_hasta,
                    total_recuperado=float(totales_periodo[segmento.periodo]),
                )
                for segmento in segmentos
            ],
            agrupaciones=datos,
        )
