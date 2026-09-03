import calendar
import logging
from datetime import date, datetime, timedelta

from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from app.modules.negocios.colocacion.resumen.repositories.sql_colocacion_resumen_repository import (
    PeriodosComparacionColocacion,
    SqlColocacionResumenRepository,
    TotalesColocacion,
)
from app.modules.negocios.colocacion.resumen.schemas import (
    FilaResumenColocacion,
    InputResumenColocacion,
    ResumenColocacionResponse,
)


logger = logging.getLogger("uvicorn.error")


class ResumenColocacionService:
    def __init__(self, repository: SqlColocacionResumenRepository) -> None:
        self.repository = repository

    def obtener_resumen(
        self,
        input_data: InputResumenColocacion,
        auth_context: AuthContext,
    ) -> ResumenColocacionResponse:
        fecha_sistema = auth_context.usuario.fecha_sistema
        fecha_hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        if input_data.fecha_fin > fecha_hoy:
            raise HTTPException(
                status_code=400,
                detail="fecha_fin no puede ser posterior a la fecha del sistema.",
            )

        try:
            periodos = self._construir_periodos(input_data.fecha_inicio, input_data.fecha_fin)
            agencia_ids = list(dict.fromkeys(input_data.agencia_ids))
            return ResumenColocacionResponse(
                fecha_inicio=input_data.fecha_inicio,
                fecha_fin=input_data.fecha_fin,
                fecha_inicio_periodo_anterior=periodos.anterior_inicio,
                fecha_fin_periodo_anterior=periodos.anterior_fin,
                fecha_inicio_mes_a_fecha=periodos.mes_a_fecha_inicio,
                fecha_fin_mes_a_fecha=periodos.mes_a_fecha_fin,
                fecha_inicio_mes_anterior_mismo_dia=periodos.mes_anterior_inicio,
                fecha_fin_mes_anterior_mismo_dia=periodos.mes_anterior_fin,
                resumen_por_agencia=self._filas(
                    self.repository.obtener_por_agencia(agencia_ids, periodos)
                ),
                por_tipo_prestamo=self._filas(
                    self.repository.obtener_por_dimension(
                        agencia_ids, periodos, "tipo_prestamo"
                    )
                ),
                por_producto=self._filas(
                    self.repository.obtener_por_dimension(agencia_ids, periodos, "producto")
                ),
                por_segmento=self._filas(
                    self.repository.obtener_por_dimension(agencia_ids, periodos, "segmento")
                ),
                por_condicion=self._filas(
                    self.repository.obtener_por_dimension(agencia_ids, periodos, "condicion")
                ),
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error consultando resumen de colocacion")
            raise HTTPException(
                status_code=500,
                detail="Error consultando resumen de colocacion.",
            ) from exc

    @staticmethod
    def _construir_periodos(fecha_inicio: date, fecha_fin: date) -> PeriodosComparacionColocacion:
        mes_a_fecha_inicio = fecha_fin.replace(day=1)
        mes_anterior_fin = mes_a_fecha_inicio - timedelta(days=1)
        mes_anterior_inicio = mes_anterior_fin.replace(day=1)
        return PeriodosComparacionColocacion(
            actual_inicio=fecha_inicio,
            actual_fin=fecha_fin,
            # El comparativo mensual usa el cierre completo del mes anterior.
            anterior_inicio=mes_anterior_inicio,
            anterior_fin=mes_anterior_fin,
            mes_a_fecha_inicio=mes_a_fecha_inicio,
            mes_a_fecha_fin=fecha_fin,
            # El comparativo MTD llega al mismo día calendario del mes anterior.
            mes_anterior_inicio=mes_anterior_inicio,
            mes_anterior_fin=_mover_mes(fecha_fin, -1),
        )

    @staticmethod
    def _filas(totales: list[TotalesColocacion]) -> list[FilaResumenColocacion]:
        return [
            FilaResumenColocacion(
                id_agencia=item.id_agencia,
                agencia=item.agencia,
                dimension=item.dimension,
                monto_colocado=_monto(item.monto_colocado),
                monto_colocado_periodo_anterior=_monto(item.monto_colocado_periodo_anterior),
                variacion_valor=_monto(
                    item.monto_colocado - item.monto_colocado_periodo_anterior
                ),
                variacion_porcentaje=_porcentaje_variacion(
                    item.monto_colocado,
                    item.monto_colocado_periodo_anterior,
                ),
                monto_mes_a_fecha=_monto(item.monto_mes_a_fecha),
                monto_mes_anterior_mismo_dia=_monto(item.monto_mes_anterior_mismo_dia),
                variacion_mes_a_fecha_valor=_monto(
                    item.monto_mes_a_fecha - item.monto_mes_anterior_mismo_dia
                ),
                variacion_mes_a_fecha_porcentaje=_porcentaje_variacion(
                    item.monto_mes_a_fecha,
                    item.monto_mes_anterior_mismo_dia,
                ),
            )
            for item in totales
        ]


def _mover_mes(fecha: date, cantidad_meses: int) -> date:
    indice_mes = fecha.year * 12 + fecha.month - 1 + cantidad_meses
    anio, mes_base_cero = divmod(indice_mes, 12)
    mes = mes_base_cero + 1
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, min(fecha.day, ultimo_dia))


def _porcentaje_variacion(actual: float, anterior: float) -> float | None:
    if anterior == 0:
        return None
    return round(((actual - anterior) / anterior) * 100, 2)


def _monto(valor: float) -> float:
    return round(valor, 2)
