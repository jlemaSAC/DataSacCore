import calendar
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from fastapi import HTTPException

from app.modules.analytic.recuperacion.recuperacion_historico.domain import (
    ResultadoResumenRecuperacion,
)
from app.modules.analytic.recuperacion.recuperacion_historico.service import (
    RecuperacionHistoricoService,
)
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.recuperacion.resumen.schemas import (
    AgrupacionesResumenRecuperacion,
    FilaAgrupacionRecuperacion,
    InputResumenRecuperacion,
    ResumenRecuperacionResponse,
)


logger = logging.getLogger("uvicorn.error")
TIPOS_DIMENSION = (
    "agencia",
    "asesor",
    "cargo",
    "tipo_prestamo",
    "producto",
    "condicion",
    "tipo_cobro",
    "abogado",
)


@dataclass(frozen=True)
class PeriodosComparacionRecuperacion:
    actual_inicio: date
    actual_fin: date
    anterior_inicio: date
    anterior_fin: date
    mismo_rango_anterior_inicio: date
    mismo_rango_anterior_fin: date


@dataclass
class _ComparativoRecuperacion:
    agencia: str | None
    dimension: str
    numero_operaciones: int = 0
    numero_operaciones_periodo_anterior: int = 0
    numero_operaciones_mismo_rango_mes_anterior: int = 0
    monto_recuperado: float = 0.0
    monto_recuperado_periodo_anterior: float = 0.0
    monto_mismo_rango_mes_anterior: float = 0.0


class ResumenRecuperacionService:
    def __init__(self, recuperacion_historico_service: RecuperacionHistoricoService) -> None:
        self.recuperacion_historico_service = recuperacion_historico_service

    def obtener_resumen(
        self,
        input_data: InputResumenRecuperacion,
        auth_context: AuthContext,
    ) -> ResumenRecuperacionResponse:
        fecha_sistema = auth_context.usuario.fecha_sistema
        fecha_hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        if input_data.fecha_fin > fecha_hoy:
            raise HTTPException(
                status_code=400,
                detail="fecha_fin no puede ser posterior a la fecha del sistema.",
            )

        try:
            periodos = self._construir_periodos(input_data.fecha_inicio, input_data.fecha_fin)
            comparativos, asesores_disponibles, cargos_disponibles = self._obtener_comparativos(
                input_data.agencias,
                input_data.asesores,
                input_data.cargos,
                periodos,
                fecha_hoy,
            )
            return ResumenRecuperacionResponse(
                fecha_inicio=periodos.actual_inicio,
                fecha_fin=periodos.actual_fin,
                fecha_inicio_periodo_anterior=periodos.anterior_inicio,
                fecha_fin_periodo_anterior=periodos.anterior_fin,
                fecha_inicio_mismo_rango_mes_anterior=periodos.mismo_rango_anterior_inicio,
                fecha_fin_mismo_rango_mes_anterior=periodos.mismo_rango_anterior_fin,
                asesores_disponibles=sorted(asesores_disponibles, key=str.casefold),
                cargos_disponibles=sorted(cargos_disponibles, key=str.casefold),
                agrupaciones=AgrupacionesResumenRecuperacion(
                    por_agencia=_filas(comparativos["agencia"]),
                    por_asesor=_filas(comparativos["asesor"]),
                    por_cargo=_filas(comparativos["cargo"]),
                    por_tipo_prestamo=_filas(comparativos["tipo_prestamo"]),
                    por_producto=_filas(comparativos["producto"]),
                    por_condicion=_filas(comparativos["condicion"]),
                    por_tipo_cobro=_filas(comparativos["tipo_cobro"]),
                    por_abogado=_filas(comparativos["abogado"]),
                ),
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Error consultando resumen de recuperacion")
            raise HTTPException(
                status_code=500,
                detail="Error consultando resumen de recuperacion.",
            ) from exc

    def _obtener_comparativos(
        self,
        agencias: list[str],
        asesores: list[str],
        cargos: list[str],
        periodos: PeriodosComparacionRecuperacion,
        fecha_hoy: date,
    ) -> tuple[
        dict[str, dict[tuple[str | None, str], _ComparativoRecuperacion]],
        set[str],
        set[str],
    ]:
        comparativos: dict[
            str, dict[tuple[str | None, str], _ComparativoRecuperacion]
        ] = {dimension: {} for dimension in TIPOS_DIMENSION}
        asesores_disponibles: set[str] = set()
        cargos_disponibles: set[str] = set()
        rangos = (
            ("actual", periodos.actual_inicio, periodos.actual_fin),
            ("anterior", periodos.anterior_inicio, periodos.anterior_fin),
            (
                "mismo_rango_anterior",
                periodos.mismo_rango_anterior_inicio,
                periodos.mismo_rango_anterior_fin,
            ),
        )
        for nombre, fecha_inicio, fecha_fin in rangos:
            resultado: ResultadoResumenRecuperacion = (
                self.recuperacion_historico_service.obtener_agrupaciones_resumen_por_rango(
                    fecha_inicio,
                    fecha_fin,
                    fecha_hoy,
                    agencias,
                    asesores,
                    cargos,
                )
            )
            asesores_disponibles.update(resultado.asesores_disponibles)
            cargos_disponibles.update(resultado.cargos_disponibles)
            for tipo_dimension, agrupaciones in resultado.agrupaciones.items():
                for agrupacion in agrupaciones:
                    clave = (agrupacion.agencia, agrupacion.dimension)
                    fila = comparativos[tipo_dimension].setdefault(
                        clave,
                        _ComparativoRecuperacion(
                            agencia=agrupacion.agencia,
                            dimension=agrupacion.dimension,
                        ),
                    )
                    if nombre == "actual":
                        fila.numero_operaciones += agrupacion.numero_operaciones
                        fila.monto_recuperado += agrupacion.monto_recuperado
                    elif nombre == "anterior":
                        fila.numero_operaciones_periodo_anterior += agrupacion.numero_operaciones
                        fila.monto_recuperado_periodo_anterior += agrupacion.monto_recuperado
                    else:
                        fila.numero_operaciones_mismo_rango_mes_anterior += (
                            agrupacion.numero_operaciones
                        )
                        fila.monto_mismo_rango_mes_anterior += agrupacion.monto_recuperado
        return comparativos, asesores_disponibles, cargos_disponibles

    @staticmethod
    def _construir_periodos(
        fecha_inicio: date,
        fecha_fin: date,
    ) -> PeriodosComparacionRecuperacion:
        mes_anterior_fin = fecha_fin.replace(day=1) - timedelta(days=1)
        return PeriodosComparacionRecuperacion(
            actual_inicio=fecha_inicio,
            actual_fin=fecha_fin,
            anterior_inicio=mes_anterior_fin.replace(day=1),
            anterior_fin=mes_anterior_fin,
            mismo_rango_anterior_inicio=_mover_mes(fecha_inicio, -1),
            mismo_rango_anterior_fin=_mover_mes(fecha_fin, -1),
        )


def _filas(
    comparativos: dict[tuple[str | None, str], _ComparativoRecuperacion],
) -> list[FilaAgrupacionRecuperacion]:
    return [
        FilaAgrupacionRecuperacion(
            agencia=fila.agencia,
            dimension=fila.dimension,
            numero_operaciones=fila.numero_operaciones,
            numero_operaciones_periodo_anterior=fila.numero_operaciones_periodo_anterior,
            numero_operaciones_mismo_rango_mes_anterior=(
                fila.numero_operaciones_mismo_rango_mes_anterior
            ),
            variacion_operaciones=(
                fila.numero_operaciones - fila.numero_operaciones_mismo_rango_mes_anterior
            ),
            monto_recuperado=round(fila.monto_recuperado, 2),
            monto_recuperado_periodo_anterior=round(
                fila.monto_recuperado_periodo_anterior, 2
            ),
            monto_mismo_rango_mes_anterior=round(
                fila.monto_mismo_rango_mes_anterior, 2
            ),
            variacion_valor=round(
                fila.monto_recuperado - fila.monto_mismo_rango_mes_anterior, 2
            ),
        )
        for fila in sorted(
            comparativos.values(),
            key=lambda item: (item.agencia or "", item.dimension),
        )
    ]


def _mover_mes(fecha: date, cantidad_meses: int) -> date:
    indice_mes = fecha.year * 12 + fecha.month - 1 + cantidad_meses
    anio, mes_base_cero = divmod(indice_mes, 12)
    mes = mes_base_cero + 1
    return date(anio, mes, min(fecha.day, calendar.monthrange(anio, mes)[1]))
