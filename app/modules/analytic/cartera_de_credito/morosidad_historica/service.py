import calendar
import logging
from datetime import date, datetime
from time import perf_counter

from fastapi import HTTPException

from app.modules.analytic.cartera_de_credito.morosidad_historica.domain import (
    CorteActualMorosidad,
    MorosidadAgrupada,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.repositories.mongo_morosidad_historica_repository import (
    MongoMorosidadHistoricaRepository,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.schemas import (
    InputMorosidadHistorica,
    MorosidadHistoricaAgrupacion,
    MorosidadHistoricaResponse,
)
from app.modules.auth.schemas import AuthContext


logger = logging.getLogger("uvicorn.error")
MAX_MESES_RANGO = 60


class MorosidadHistoricaService:
    def __init__(self, repository: MongoMorosidadHistoricaRepository) -> None:
        self.repository = repository

    def obtener_morosidad_historica(
        self,
        input_data: InputMorosidadHistorica,
        auth_context: AuthContext,
    ) -> MorosidadHistoricaResponse:
        inicio_total = perf_counter()
        try:
            inicio_cortes = perf_counter()
            cortes, corte_actual = self._construir_cortes(input_data, auth_context)
            cortes_ms = (perf_counter() - inicio_cortes) * 1000

            inicio_repositorio = perf_counter()
            agrupaciones = self.repository.obtener_morosidad_agrupada(
                cortes,
                corte_actual,
            )
            repositorio_ms = (perf_counter() - inicio_repositorio) * 1000

            inicio_respuesta = perf_counter()
            respuesta = self._construir_respuesta(agrupaciones)
            respuesta_ms = (perf_counter() - inicio_respuesta) * 1000
            total_ms = (perf_counter() - inicio_total) * 1000
            print(
                "[morosidad-historica][service] "
                f"periodo={input_data.periodo_desde}:{input_data.periodo_hasta} "
                f"cortes_ms={cortes_ms:.2f} "
                f"repositorio_ms={repositorio_ms:.2f} "
                f"respuesta_ms={respuesta_ms:.2f} "
                f"total_ms={total_ms:.2f}"
            )
            return respuesta
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception(
                "Error consultando morosidad historica entre %s y %s",
                input_data.periodo_desde,
                input_data.periodo_hasta,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error consultando morosidad historica: {exc}",
            ) from exc

    @staticmethod
    def _construir_cortes(
        input_data: InputMorosidadHistorica,
        auth_context: AuthContext,
    ) -> tuple[dict[str, tuple[int, int]], CorteActualMorosidad | None]:
        anio_desde, mes_desde = map(int, input_data.periodo_desde.split("-"))
        anio_hasta, mes_hasta = map(int, input_data.periodo_hasta.split("-"))
        cantidad_meses = (anio_hasta - anio_desde) * 12 + mes_hasta - mes_desde + 1
        if cantidad_meses > MAX_MESES_RANGO:
            raise HTTPException(
                status_code=400,
                detail=f"El rango no puede superar {MAX_MESES_RANGO} meses.",
            )

        fecha_sistema = auth_context.usuario.fecha_sistema
        hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        if (anio_hasta, mes_hasta) > (hoy.year, hoy.month):
            raise HTTPException(
                status_code=400,
                detail="periodo_hasta no puede ser posterior al mes actual.",
            )

        cortes: dict[str, tuple[int, int]] = {}
        corte_actual: CorteActualMorosidad | None = None
        anio, mes = anio_desde, mes_desde
        while (anio, mes) <= (anio_hasta, mes_hasta):
            if (anio, mes) == (hoy.year, hoy.month):
                corte_actual = CorteActualMorosidad(
                    fecha_corte=hoy.strftime("%Y%m%d"),
                    anio=anio,
                    mes=mes,
                )
            else:
                ultimo_dia = calendar.monthrange(anio, mes)[1]
                cortes[f"{anio:04d}{mes:02d}{ultimo_dia:02d}"] = (anio, mes)
            if mes == 12:
                anio, mes = anio + 1, 1
            else:
                mes += 1
        return cortes, corte_actual

    @staticmethod
    def _construir_respuesta(
        agrupaciones: list[MorosidadAgrupada],
    ) -> MorosidadHistoricaResponse:
        return MorosidadHistoricaResponse(
            agrupaciones=[
                MorosidadHistoricaAgrupacion(
                    **agrupacion.dimensiones.__dict__,
                    operaciones=agrupacion.operaciones,
                    saldo_capital=round(agrupacion.saldo_capital, 2),
                    cartera_improductiva=round(agrupacion.cartera_improductiva, 2),
                    provision_requerida=round(agrupacion.provision_requerida, 2),
                )
                for agrupacion in sorted(
                    agrupaciones,
                    key=lambda item: item.dimensiones,
                )
            ],
        )
