import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

from fastapi import HTTPException

from app.modules.analytic.cartera_de_credito.comparativo_cartera.domain import (
    TotalesCartera,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.repositories.mongo_comparativo_cartera_repository import (
    MongoComparativoCarteraRepository,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.repositories.redis_comparativo_cartera_cache import (
    RedisComparativoCarteraCache,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.schemas import (
    ComparativoMorosidadRango,
    ComparativoCarteraResponse,
    CorteComparativoCartera,
    InputComparativoCartera,
    PuntoComparativoCartera,
    ResumenCarteraAgencia,
    ResumenMorosidadRango,
)
from app.modules.auth.schemas import AuthContext


logger = logging.getLogger("uvicorn.error")


class ComparativoCarteraService:
    def __init__(
        self,
        repository: MongoComparativoCarteraRepository,
        cache: RedisComparativoCarteraCache | None = None,
    ) -> None:
        self.repository = repository
        self.cache = cache or RedisComparativoCarteraCache(None)

    def obtener_comparativo(
        self,
        input_data: InputComparativoCartera,
        auth_context: AuthContext,
    ) -> ComparativoCarteraResponse:
        fecha_sistema = auth_context.usuario.fecha_sistema
        hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        if input_data.fecha_hasta > hoy:
            raise HTTPException(
                status_code=400,
                detail="fecha_hasta no puede ser posterior a la fecha del sistema.",
            )

        fechas_actuales = self._rango_fechas(
            input_data.fecha_desde,
            input_data.fecha_hasta,
        )
        fecha_mes_anterior = self._cierre_mes_anterior(input_data.fecha_desde)
        fecha_anio_anterior = self._cierre_anio_anterior(input_data.fecha_desde)
        fechas_historicas = {
            fecha for fecha in fechas_actuales if fecha != hoy
        } | {fecha_mes_anterior, fecha_anio_anterior}

        try:
            totales = self.cache.obtener(
                fechas_historicas,
                input_data.agencias,
                input_data.filtrar_diferidos,
            )
            fechas_faltantes = fechas_historicas - totales.keys()
            consultar_actual = hoy in fechas_actuales
            cantidad_consultas = int(bool(fechas_faltantes)) + int(consultar_actual)
            if cantidad_consultas:
                with ThreadPoolExecutor(max_workers=cantidad_consultas) as executor:
                    historico_future = (
                        executor.submit(
                            self.repository.obtener_historico,
                            fechas_faltantes,
                            input_data.agencias,
                            input_data.filtrar_diferidos,
                        )
                        if fechas_faltantes
                        else None
                    )
                    actual_future = (
                        executor.submit(
                            self.repository.obtener_actual,
                            hoy,
                            input_data.agencias,
                            input_data.filtrar_diferidos,
                        )
                        if consultar_actual
                        else None
                    )
                    nuevos_totales: dict[date, TotalesCartera] = {}
                    if historico_future is not None:
                        nuevos_totales.update(historico_future.result())
                    totales.update(nuevos_totales)
                    self.cache.guardar(
                        nuevos_totales.values(),
                        input_data.agencias,
                        input_data.filtrar_diferidos,
                    )
                    if actual_future is not None:
                        actual = actual_future.result()
                        if actual is not None:
                            totales[hoy] = actual
            totales_por_agencia = self.repository.obtener_por_agencia(
                input_data.fecha_hasta,
                input_data.filtrar_diferidos,
                actual=input_data.fecha_hasta == hoy,
            )
        except Exception as exc:
            logger.exception(
                "Error consultando comparativo de cartera entre %s y %s",
                input_data.fecha_desde,
                input_data.fecha_hasta,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error consultando comparativo de cartera: {exc}",
            ) from exc

        corte_mes_anterior = self._construir_corte(totales.get(fecha_mes_anterior))
        corte_anio_anterior = self._construir_corte(totales.get(fecha_anio_anterior))
        puntos = [
            PuntoComparativoCartera(
                fecha=fecha,
                actual=self._construir_corte(totales.get(fecha)),
                mes_anterior=corte_mes_anterior,
                anio_anterior=corte_anio_anterior,
            )
            for fecha in fechas_actuales
        ]
        return ComparativoCarteraResponse(
            fecha_desde=input_data.fecha_desde,
            fecha_hasta=input_data.fecha_hasta,
            consolidado=not input_data.agencias,
            agencias=input_data.agencias,
            filtrar_diferidos=input_data.filtrar_diferidos,
            resumen_morosidad=ComparativoMorosidadRango(
                actual=self._resumir_morosidad([punto.actual for punto in puntos]),
                mes_anterior=self._resumir_morosidad([corte_mes_anterior]),
                anio_anterior=self._resumir_morosidad([corte_anio_anterior]),
            ),
            resumen_por_agencia=[
                ResumenCarteraAgencia(
                    agencia=agencia,
                    saldo_capital=round(agencia_totales.saldo_capital, 2),
                    morosidad_porcentaje=round(agencia_totales.morosidad * 100, 2),
                    cartera_improductiva=round(
                        agencia_totales.cartera_improductiva, 2
                    ),
                    provision_requerida=round(
                        agencia_totales.provision_requerida, 2
                    ),
                )
                for agencia, agencia_totales in sorted(totales_por_agencia.items())
            ],
            puntos=puntos,
        )

    @staticmethod
    def _rango_fechas(fecha_desde: date, fecha_hasta: date) -> list[date]:
        cantidad = (fecha_hasta - fecha_desde).days + 1
        return [fecha_desde + timedelta(days=offset) for offset in range(cantidad)]

    @staticmethod
    def _cierre_mes_anterior(fecha: date) -> date:
        return fecha.replace(day=1) - timedelta(days=1)

    @staticmethod
    def _cierre_anio_anterior(fecha: date) -> date:
        return date(fecha.year - 1, 12, 31)

    @staticmethod
    def _construir_corte(
        totales: TotalesCartera | None,
    ) -> CorteComparativoCartera | None:
        if totales is None:
            return None
        morosidad = totales.morosidad
        return CorteComparativoCartera(
            fecha_corte=totales.fecha_corte,
            operaciones=totales.operaciones,
            saldo_capital=round(totales.saldo_capital, 2),
            capital_vigente=round(totales.capital_vigente, 2),
            capital_no_devenga=round(totales.capital_no_devenga, 2),
            capital_vencido=round(totales.capital_vencido, 2),
            cartera_improductiva=round(totales.cartera_improductiva, 2),
            provision_requerida=round(totales.provision_requerida, 2),
            morosidad=round(morosidad, 6),
            morosidad_porcentaje=round(morosidad * 100, 2),
        )

    @staticmethod
    def _resumir_morosidad(
        cortes: list[CorteComparativoCartera | None],
    ) -> ResumenMorosidadRango:
        disponibles = [corte for corte in cortes if corte is not None]
        if not disponibles:
            return ResumenMorosidadRango(
                fecha_desde=None,
                fecha_hasta=None,
                dias_con_datos=0,
                morosidad_inicial_porcentaje=None,
                morosidad_final_porcentaje=None,
                morosidad_promedio_ponderada_porcentaje=None,
                morosidad_minima_porcentaje=None,
                morosidad_maxima_porcentaje=None,
                variacion_puntos_porcentuales=None,
            )

        saldo_acumulado = sum(corte.saldo_capital for corte in disponibles)
        cartera_improductiva_acumulada = sum(
            corte.cartera_improductiva for corte in disponibles
        )
        promedio_ponderado = (
            cartera_improductiva_acumulada / saldo_acumulado * 100
            if saldo_acumulado
            else 0.0
        )
        morosidad_inicial = disponibles[0].morosidad_porcentaje
        morosidad_final = disponibles[-1].morosidad_porcentaje
        porcentajes = [corte.morosidad_porcentaje for corte in disponibles]
        return ResumenMorosidadRango(
            fecha_desde=disponibles[0].fecha_corte,
            fecha_hasta=disponibles[-1].fecha_corte,
            dias_con_datos=len(disponibles),
            morosidad_inicial_porcentaje=morosidad_inicial,
            morosidad_final_porcentaje=morosidad_final,
            morosidad_promedio_ponderada_porcentaje=round(promedio_ponderado, 2),
            morosidad_minima_porcentaje=min(porcentajes),
            morosidad_maxima_porcentaje=max(porcentajes),
            variacion_puntos_porcentuales=round(
                morosidad_final - morosidad_inicial,
                2,
            ),
        )
