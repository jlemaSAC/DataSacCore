import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import get_args

from fastapi import HTTPException

from app.modules.analytic.cartera_de_credito.comparativo_cartera.domain import (
    DimensionCartera,
    PrestamoResumenCartera,
    TotalesCartera,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.repositories.sql_clientes_cartera_repository import (
    SqlClientesCarteraRepository,
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
    FilaResumenCartera,
    PuntoComparativoCartera,
    ResumenCarteraAgencia,
    ResumenCarteraDimension,
    ResumenMorosidadRango,
)
from app.modules.auth.schemas import AuthContext


logger = logging.getLogger("uvicorn.error")


@dataclass
class _AcumuladoResumen:
    saldo: Decimal = Decimal(0)
    improductiva: Decimal = Decimal(0)
    provision: Decimal = Decimal(0)
    operaciones: int = 0
    clientes: set[str] = field(default_factory=set)


class ComparativoCarteraService:
    def __init__(
        self,
        repository: MongoComparativoCarteraRepository,
        cache: RedisComparativoCarteraCache | None = None,
        clientes_repository: SqlClientesCarteraRepository | None = None,
    ) -> None:
        self.repository = repository
        self.cache = cache or RedisComparativoCarteraCache(None)
        self.clientes_repository = clientes_repository

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
            fecha_corte_resumen = max(
                (fecha for fecha in fechas_actuales if fecha in totales), default=None,
            )
            resumen_por_dimension = []
            if fecha_corte_resumen is not None:
                prestamos = self.repository.obtener_prestamos_resumen(
                    fecha_corte_resumen,
                    input_data.agencias,
                    input_data.filtrar_diferidos,
                    actual=fecha_corte_resumen == hoy,
                )
                sin_cliente = [item.numero_prestamo for item in prestamos if not item.cliente]
                clientes: dict[str, str] = {}
                if sin_cliente:
                    if self.clientes_repository is None:
                        raise ValueError("No hay repositorio para completar los clientes del corte.")
                    clientes = self.clientes_repository.obtener_clientes(sin_cliente)
                    if any(numero not in clientes for numero in sin_cliente):
                        raise ValueError("Hay prestamos del corte sin cliente principal identificado.")
                resumen_por_dimension = self._resumir_dimensiones(prestamos, clientes)
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
            fecha_corte_resumen=fecha_corte_resumen,
            resumen_por_dimension=resumen_por_dimension,
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
    def _resumir_dimensiones(
        prestamos: list[PrestamoResumenCartera], clientes: dict[str, str],
    ) -> list[ResumenCarteraDimension]:
        dimensiones: tuple[DimensionCartera, ...] = get_args(DimensionCartera)
        grupos: dict[DimensionCartera, dict[str, _AcumuladoResumen]] = {
            dimension: {} for dimension in dimensiones
        }
        saldo_total = sum((Decimal(str(item.saldo_capital)) for item in prestamos), Decimal(0))
        for item in prestamos:
            cliente = item.cliente or clientes.get(item.numero_prestamo)
            for dimension in dimensiones:
                campo = item.dimensiones.get(dimension, "").strip().upper() or "SIN DATOS"
                acumulado = grupos[dimension].setdefault(campo, _AcumuladoResumen())
                acumulado.saldo += Decimal(str(item.saldo_capital))
                acumulado.improductiva += Decimal(str(item.cartera_improductiva))
                acumulado.provision += Decimal(str(item.provision_requerida))
                acumulado.operaciones += 1
                if cliente:
                    acumulado.clientes.add(cliente)
        return [ResumenCarteraDimension(
            dimension=dimension,
            filas=[FilaResumenCartera(
                campo=campo,
                saldo_capital=round(float(item.saldo), 2),
                participacion_saldo_porcentaje=(
                    round(float(item.saldo / saldo_total * 100), 2) if saldo_total else 0.0
                ),
                operaciones=item.operaciones,
                clientes=len(item.clientes),
                provision_requerida=round(float(item.provision), 2),
                morosidad_porcentaje=(
                    round(float(item.improductiva / item.saldo * 100), 2) if item.saldo else 0.0
                ),
            ) for campo, item in sorted(
                grupos[dimension].items(), key=lambda par: (-par[1].saldo, par[0]),
            )],
        ) for dimension in dimensiones]

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
