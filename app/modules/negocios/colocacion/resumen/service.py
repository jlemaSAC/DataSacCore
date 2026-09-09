import calendar
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from fastapi import HTTPException

from app.modules.analytic.colocacion.colocacion_historico.domain import (
    DimensionesColocacion,
)
from app.modules.analytic.colocacion.colocacion_historico.service import (
    ColocacionHistoricoService,
)
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.colocacion.resumen.schemas import (
    DetalleResumenColocacionResponse,
    FilaDetalleColocacion,
    FilaComparativaColocacion,
    InputDetalleResumenColocacion,
    InputResumenColocacion,
    ResumenColocacionResponse,
)


logger = logging.getLogger("uvicorn.error")
MAX_MESES_RANGO = 60


@dataclass
class _ComparativoColocacion:
    dimensiones: DimensionesColocacion
    saldo_inicial: float = 0.0
    saldo_inicial_periodo_anterior: float = 0.0
    saldo_inicial_mismo_rango_mes_anterior: float = 0.0


@dataclass(frozen=True)
class PeriodosComparacionColocacion:
    actual_inicio: date
    actual_fin: date
    anterior_inicio: date
    anterior_fin: date
    mismo_rango_anterior_inicio: date
    mismo_rango_anterior_fin: date


class ResumenColocacionService:
    """Resumen comparativo construido sobre el mismo hecho dimensional de Analítica."""

    def __init__(self, colocacion_historico_service: ColocacionHistoricoService) -> None:
        self.colocacion_historico_service = colocacion_historico_service

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
        if _cantidad_meses(input_data.fecha_inicio, input_data.fecha_fin) > MAX_MESES_RANGO:
            raise HTTPException(
                status_code=400,
                detail=f"El rango no puede superar {MAX_MESES_RANGO} meses.",
            )

        try:
            agencias = list(dict.fromkeys(agencia.strip() for agencia in input_data.agencias))
            periodos = self._construir_periodos(input_data.fecha_inicio, input_data.fecha_fin)
            comparativos = self._obtener_comparativos(agencias, periodos, fecha_hoy)
            return ResumenColocacionResponse(
                fecha_inicio=periodos.actual_inicio,
                fecha_fin=periodos.actual_fin,
                fecha_inicio_periodo_anterior=periodos.anterior_inicio,
                fecha_fin_periodo_anterior=periodos.anterior_fin,
                fecha_inicio_mismo_rango_mes_anterior=periodos.mismo_rango_anterior_inicio,
                fecha_fin_mismo_rango_mes_anterior=periodos.mismo_rango_anterior_fin,
                agrupaciones=self._filas_comparativas(comparativos),
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error consultando resumen de colocacion")
            raise HTTPException(
                status_code=500,
                detail="Error consultando resumen de colocacion.",
            ) from exc

    def obtener_detalle(
        self,
        input_data: InputDetalleResumenColocacion,
        auth_context: AuthContext,
    ) -> DetalleResumenColocacionResponse:
        fecha_hoy = _fecha_sistema(auth_context)
        if input_data.fecha_fin > fecha_hoy:
            raise HTTPException(
                status_code=400,
                detail="fecha_fin no puede ser posterior a la fecha del sistema.",
            )
        if _cantidad_meses(input_data.fecha_inicio, input_data.fecha_fin) > MAX_MESES_RANGO:
            raise HTTPException(
                status_code=400,
                detail=f"El rango no puede superar {MAX_MESES_RANGO} meses.",
            )

        try:
            agencias = list(dict.fromkeys(agencia.strip() for agencia in input_data.agencias))
            asesores = list(dict.fromkeys(asesor.strip() for asesor in input_data.asesores))
            detalles = self.colocacion_historico_service.obtener_detalles_resumen_por_rango(
                input_data.fecha_inicio,
                input_data.fecha_fin,
                fecha_hoy,
                agencias,
                input_data.dimension,
                input_data.valor_dimension.strip(),
                asesores,
            )
            inicio = (input_data.pagina - 1) * input_data.tamano_pagina
            items = detalles[inicio : inicio + input_data.tamano_pagina]
            return DetalleResumenColocacionResponse(
                fecha_inicio=input_data.fecha_inicio,
                fecha_fin=input_data.fecha_fin,
                dimension=input_data.dimension,
                valor_dimension=input_data.valor_dimension.strip(),
                pagina=input_data.pagina,
                tamano_pagina=input_data.tamano_pagina,
                total_registros=len(detalles),
                total_monto_colocado=_monto(sum(detalle.monto_colocado for detalle in detalles)),
                items=[
                    FilaDetalleColocacion(
                        numero_cliente=detalle.numero_cliente,
                        nombre_cliente=detalle.nombre_cliente,
                        numero_operacion=detalle.numero_operacion,
                        agencia=detalle.agencia,
                        asesor=detalle.asesor,
                        tipo_condicion=detalle.tipo_condicion,
                        producto=detalle.producto,
                        tipo_prestamo=detalle.tipo_prestamo,
                        segmento=detalle.segmento,
                        tasa_nominal=detalle.tasa_nominal,
                        tasa_real=detalle.tasa_real,
                        monto_colocado=_monto(detalle.monto_colocado),
                    )
                    for detalle in items
                ],
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error consultando detalle de resumen de colocacion")
            raise HTTPException(
                status_code=500,
                detail="Error consultando detalle de resumen de colocacion.",
            ) from exc

    def _obtener_comparativos(
        self,
        agencias: list[str],
        periodos: PeriodosComparacionColocacion,
        fecha_hoy: date,
    ) -> dict[tuple, _ComparativoColocacion]: # type: ignore
        rangos = (
            ("actual", periodos.actual_inicio, periodos.actual_fin),
            ("anterior", periodos.anterior_inicio, periodos.anterior_fin),
            (
                "mismo_rango_anterior",
                periodos.mismo_rango_anterior_inicio,
                periodos.mismo_rango_anterior_fin,
            ),
        )
        comparativos: dict[tuple, _ComparativoColocacion] = {} # type: ignore
        for nombre, fecha_inicio, fecha_fin in rangos:
            agrupaciones = self.colocacion_historico_service.obtener_agrupaciones_resumen_por_rango(
                fecha_inicio,
                fecha_fin,
                fecha_hoy,
                agencias,
            )
            for dimensiones, agrupacion in agrupaciones.items():
                fila = comparativos.setdefault(
                    _clave_dimensiones(dimensiones), _ComparativoColocacion(dimensiones)
                )
                if nombre == "actual":
                    fila.saldo_inicial += agrupacion.saldo_inicial
                elif nombre == "anterior":
                    fila.saldo_inicial_periodo_anterior += agrupacion.saldo_inicial
                else:
                    fila.saldo_inicial_mismo_rango_mes_anterior += agrupacion.saldo_inicial
        return comparativos

    @staticmethod
    def _construir_periodos(fecha_inicio: date, fecha_fin: date) -> PeriodosComparacionColocacion:
        mismo_rango_anterior_fin = _mover_mes(fecha_fin, -1)
        mes_anterior_completo_fin = fecha_fin.replace(day=1) - timedelta(days=1)
        return PeriodosComparacionColocacion(
            actual_inicio=fecha_inicio,
            actual_fin=fecha_fin,
            anterior_inicio=mes_anterior_completo_fin.replace(day=1),
            anterior_fin=mes_anterior_completo_fin,
            mismo_rango_anterior_inicio=_mover_mes(fecha_inicio, -1),
            mismo_rango_anterior_fin=mismo_rango_anterior_fin,
        )

    @staticmethod
    def _filas_comparativas(
        comparativos: dict[tuple, _ComparativoColocacion], # type: ignore
    ) -> list[FilaComparativaColocacion]:
        return [
            _fila_comparativa(fila)
            for _, fila in sorted(comparativos.items(), key=lambda item: _clave_dimensiones(item[1].dimensiones))
        ]

def _clave_dimensiones(dimensiones: DimensionesColocacion) -> tuple: # type: ignore
    return tuple(
        valor
        for campo, valor in dimensiones.__dict__.items()
        if campo not in {"periodo", "anio", "mes"}
    )


def _fila_comparativa(fila: _ComparativoColocacion) -> FilaComparativaColocacion:
    return FilaComparativaColocacion(
        agencia=fila.dimensiones.agencia,
        condicion=fila.dimensiones.condicion,
        tipo_prestamo=fila.dimensiones.tipo_prestamo,
        producto=fila.dimensiones.producto,
        segmento=fila.dimensiones.segmento,
        asesor=fila.dimensiones.asesor,
        tasa_valor=fila.dimensiones.tasa_valor,
        tasa_real=fila.dimensiones.tasa_real_valor,
        monto_colocado=_monto(fila.saldo_inicial),
        monto_colocado_periodo_anterior=_monto(fila.saldo_inicial_periodo_anterior),
        monto_mismo_rango_mes_anterior=_monto(fila.saldo_inicial_mismo_rango_mes_anterior),
        variacion_valor=_monto(fila.saldo_inicial - fila.saldo_inicial_mismo_rango_mes_anterior),
    )


def _cantidad_meses(fecha_inicio: date, fecha_fin: date) -> int:
    return (fecha_fin.year - fecha_inicio.year) * 12 + fecha_fin.month - fecha_inicio.month + 1


def _fecha_sistema(auth_context: AuthContext) -> date:
    fecha_sistema = auth_context.usuario.fecha_sistema
    return fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema


def _mover_mes(fecha: date, cantidad_meses: int) -> date:
    indice_mes = fecha.year * 12 + fecha.month - 1 + cantidad_meses
    anio, mes_base_cero = divmod(indice_mes, 12)
    mes = mes_base_cero + 1
    return date(anio, mes, min(fecha.day, calendar.monthrange(anio, mes)[1]))


def _monto(valor: float) -> float:
    return round(valor, 2)
