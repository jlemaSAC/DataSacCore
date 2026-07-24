import calendar
import logging
from collections import defaultdict
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
from app.modules.analytic.cartera_de_credito.morosidad_historica.repositories.redis_morosidad_historica_cache import (
    RedisMorosidadHistoricaCache,
    RedisMorosidadHistoricaCacheUnavailable,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.schemas import (
    InputMorosidadHistorica,
    MorosidadHistoricaAgrupacion,
    MorosidadHistoricaCacheClearResponse,
    MorosidadHistoricaResponse,
)
from app.modules.auth.schemas import AuthContext
from app.modules.auth.repositories.sql_auth_repository import SqlAuthRepository


logger = logging.getLogger("uvicorn.error")
MAX_MESES_RANGO = 60


class MorosidadHistoricaService:
    def __init__(
        self,
        repository: MongoMorosidadHistoricaRepository,
        cache: RedisMorosidadHistoricaCache | None = None,
    ) -> None:
        self.repository = repository
        self.cache = cache or RedisMorosidadHistoricaCache(None)

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

            periodos_por_corte = {
                fecha_corte: f"{anio:04d}-{mes:02d}"
                for fecha_corte, (anio, mes) in cortes.items()
            }
            inicio_cache = perf_counter()
            agrupaciones_por_periodo = self.cache.obtener_meses(periodos_por_corte.values())
            cache_ms = (perf_counter() - inicio_cache) * 1000
            cortes_faltantes = {
                fecha_corte: periodo
                for fecha_corte, periodo in cortes.items()
                if periodos_por_corte[fecha_corte] not in agrupaciones_por_periodo
            }

            inicio_repositorio = perf_counter()
            agrupaciones_faltantes = (
                self.repository.obtener_morosidad_agrupada(cortes_faltantes)
                if cortes_faltantes
                else []
            )
            if corte_actual is not None:
                agrupaciones_actuales = self.repository.obtener_morosidad_agrupada(
                    {}, corte_actual
                )
            else:
                agrupaciones_actuales = []
            repositorio_ms = (perf_counter() - inicio_repositorio) * 1000

            inicio_respuesta = perf_counter()
            agrupaciones_faltantes_por_periodo: dict[str, list[MorosidadAgrupada]] = (
                defaultdict(list)
            )
            for agrupacion in agrupaciones_faltantes:
                agrupaciones_faltantes_por_periodo[agrupacion.dimensiones.periodo].append(
                    agrupacion
                )
            for periodo in periodos_por_corte.values():
                if periodo in agrupaciones_por_periodo:
                    continue
                agrupaciones_mes = self._construir_agrupaciones(
                    agrupaciones_faltantes_por_periodo[periodo]
                )
                agrupaciones_por_periodo[periodo] = agrupaciones_mes
                self.cache.guardar_mes(periodo, agrupaciones_mes)

            respuesta = self._construir_respuesta_por_periodo(
                agrupaciones_por_periodo,
                self._construir_agrupaciones(agrupaciones_actuales),
            )
            respuesta_ms = (perf_counter() - inicio_respuesta) * 1000
            total_ms = (perf_counter() - inicio_total) * 1000
            # print(
            #     "[morosidad-historica][service] "
            #     f"periodo={input_data.periodo_desde}:{input_data.periodo_hasta} "
            #     f"cortes_ms={cortes_ms:.2f} "
            #     f"cache_ms={cache_ms:.2f} "
            #     f"cache_hits={len(agrupaciones_por_periodo) - len(cortes_faltantes)} "
            #     f"cache_misses={len(cortes_faltantes)} "
            #     f"repositorio_ms={repositorio_ms:.2f} "
            #     f"respuesta_ms={respuesta_ms:.2f} "
            #     f"total_ms={total_ms:.2f}"
            # )
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
            agrupaciones=MorosidadHistoricaService._construir_agrupaciones(agrupaciones),
        )

    @staticmethod
    def _construir_agrupaciones(
        agrupaciones: list[MorosidadAgrupada],
    ) -> list[MorosidadHistoricaAgrupacion]:
        return [
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
        ]

    @staticmethod
    def _construir_respuesta_por_periodo(
        agrupaciones_por_periodo: dict[str, list[MorosidadHistoricaAgrupacion]],
        agrupaciones_actuales: list[MorosidadHistoricaAgrupacion],
    ) -> MorosidadHistoricaResponse:
        return MorosidadHistoricaResponse(
            agrupaciones=[
                agrupacion
                for periodo in sorted(agrupaciones_por_periodo)
                for agrupacion in agrupaciones_por_periodo[periodo]
            ]
            + agrupaciones_actuales,
        )


class MorosidadHistoricaCacheAdminService:
    admin_role_code = "001"

    def __init__(
        self,
        cache: RedisMorosidadHistoricaCache,
        sql_repository: SqlAuthRepository,
    ) -> None:
        self.cache = cache
        self.sql_repository = sql_repository

    def limpiar_cache(
        self,
        auth_context: AuthContext,
    ) -> MorosidadHistoricaCacheClearResponse:
        self._validar_administrador(auth_context)
        try:
            claves_eliminadas = self.cache.limpiar_cache()
        except RedisMorosidadHistoricaCacheUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return MorosidadHistoricaCacheClearResponse(claves_eliminadas=claves_eliminadas)

    def _validar_administrador(self, auth_context: AuthContext) -> None:
        roles_usuario = self.sql_repository.get_roles_usuario(auth_context.usuario.sub)
        if not any(rol.codigo == self.admin_role_code for rol in roles_usuario):
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para limpiar la cache de morosidad historica.",
            )
