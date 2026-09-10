import calendar
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import floor

from fastapi import HTTPException

from app.modules.analytic.colocacion.colocacion_historico.domain import (
    DimensionesColocacion,
)
from app.modules.analytic.colocacion.colocacion_historico.service import (
    ColocacionHistoricoService,
)
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.colocacion.resumen.schemas import (
    AgrupacionesResumenColocacion,
    DetalleResumenColocacionResponse,
    FilaAgrupacionColocacion,
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
    numero_operaciones: int = 0
    numero_operaciones_periodo_anterior: int = 0
    numero_operaciones_mismo_rango_mes_anterior: int = 0
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
            asesores_disponibles = sorted(
                {fila.dimensiones.asesor for fila in comparativos.values()},
                key=lambda asesor: asesor.casefold(),
            )
            asesores = {asesor.strip().upper() for asesor in input_data.asesores}
            if asesores:
                comparativos = {
                    clave: fila
                    for clave, fila in comparativos.items()
                    if fila.dimensiones.asesor in asesores
                }
            return ResumenColocacionResponse(
                fecha_inicio=periodos.actual_inicio,
                fecha_fin=periodos.actual_fin,
                fecha_inicio_periodo_anterior=periodos.anterior_inicio,
                fecha_fin_periodo_anterior=periodos.anterior_fin,
                fecha_inicio_mismo_rango_mes_anterior=periodos.mismo_rango_anterior_inicio,
                fecha_fin_mismo_rango_mes_anterior=periodos.mismo_rango_anterior_fin,
                asesores_disponibles=asesores_disponibles,
                agrupaciones=_agrupar_dimensiones(self._filas_comparativas(comparativos)),
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
            inicio = (input_data.pagina - 1) * input_data.tamano_pagina
            resultado = self.colocacion_historico_service.obtener_detalles_resumen_por_rango(
                input_data.fecha_inicio,
                input_data.fecha_fin,
                fecha_hoy,
                agencias,
                input_data.dimension,
                input_data.valor_dimension.strip(),
                asesores,
                input_data.tasa_desde,
                input_data.tasa_hasta_exclusiva,
                inicio + input_data.tamano_pagina,
            )
            items = resultado.items[inicio : inicio + input_data.tamano_pagina]
            return DetalleResumenColocacionResponse(
                fecha_inicio=input_data.fecha_inicio,
                fecha_fin=input_data.fecha_fin,
                dimension=input_data.dimension,
                valor_dimension=input_data.valor_dimension.strip(),
                pagina=input_data.pagina,
                tamano_pagina=input_data.tamano_pagina,
                total_registros=resultado.total_registros,
                total_monto_colocado=_monto(resultado.total_monto_colocado),
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
                    fila.numero_operaciones += agrupacion.operaciones
                    fila.saldo_inicial += agrupacion.saldo_inicial
                elif nombre == "anterior":
                    fila.numero_operaciones_periodo_anterior += agrupacion.operaciones
                    fila.saldo_inicial_periodo_anterior += agrupacion.saldo_inicial
                else:
                    fila.numero_operaciones_mismo_rango_mes_anterior += agrupacion.operaciones
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
        numero_operaciones=fila.numero_operaciones,
        numero_operaciones_periodo_anterior=fila.numero_operaciones_periodo_anterior,
        numero_operaciones_mismo_rango_mes_anterior=fila.numero_operaciones_mismo_rango_mes_anterior,
        variacion_operaciones=(
            fila.numero_operaciones - fila.numero_operaciones_mismo_rango_mes_anterior
        ),
        monto_colocado=_monto(fila.saldo_inicial),
        monto_colocado_periodo_anterior=_monto(fila.saldo_inicial_periodo_anterior),
        monto_mismo_rango_mes_anterior=_monto(fila.saldo_inicial_mismo_rango_mes_anterior),
        variacion_valor=_monto(fila.saldo_inicial - fila.saldo_inicial_mismo_rango_mes_anterior),
    )


def _agrupar_dimensiones(
    filas: list[FilaComparativaColocacion],
) -> AgrupacionesResumenColocacion:
    return AgrupacionesResumenColocacion(
        por_agencia=_agrupar_por_dimension(filas, "agencia"),
        por_asesor=_agrupar_por_dimension(filas, "asesor", incluir_agencia=True),
        por_tipo_prestamo=_agrupar_por_dimension(filas, "tipo_prestamo"),
        por_producto=_agrupar_por_dimension(filas, "producto"),
        por_segmento=_agrupar_por_dimension(filas, "segmento"),
        por_condicion=_agrupar_por_dimension(filas, "condicion"),
        por_tasa_normal=_agrupar_por_dimension(filas, "tasa_valor"),
        por_tasa_real=_agrupar_por_dimension(filas, "tasa_real", rangos_tasa_real=True),
    )


def _agrupar_por_dimension(
    filas: list[FilaComparativaColocacion],
    campo: str,
    incluir_agencia: bool = False,
    rangos_tasa_real: bool = False,
) -> list[FilaAgrupacionColocacion]:
    agrupadas: dict[tuple[str | None, str], dict[str, str | float | int | None]] = {}
    for fila in filas:
        agencia = fila.agencia if incluir_agencia else None
        valor = getattr(fila, campo)
        tasa_desde: float | None = None
        tasa_hasta_exclusiva: float | None = None
        if rangos_tasa_real and isinstance(valor, int | float):
            tasa_desde = float(floor(valor))
            tasa_hasta_exclusiva = tasa_desde + 1
            dimension = f"{_formatear_tasa(tasa_desde)}% – {_formatear_tasa(tasa_desde + 0.99)}%"
        else:
            dimension = _etiqueta_dimension(valor)

        clave = (agencia, dimension)
        acumulado = agrupadas.setdefault(
            clave,
            {
                "agencia": agencia,
                "dimension": dimension,
                "tasa_desde": tasa_desde,
                "tasa_hasta_exclusiva": tasa_hasta_exclusiva,
                "numero_operaciones": 0,
                "numero_operaciones_periodo_anterior": 0,
                "numero_operaciones_mismo_rango_mes_anterior": 0,
                "monto_colocado": 0.0,
                "monto_colocado_periodo_anterior": 0.0,
                "monto_mismo_rango_mes_anterior": 0.0,
            },
        )
        for atributo in (
            "numero_operaciones",
            "numero_operaciones_periodo_anterior",
            "numero_operaciones_mismo_rango_mes_anterior",
            "monto_colocado",
            "monto_colocado_periodo_anterior",
            "monto_mismo_rango_mes_anterior",
        ):
            acumulado[atributo] = acumulado[atributo] + getattr(fila, atributo)  # type: ignore[operator]

    return [
        FilaAgrupacionColocacion(
            agencia=acumulado["agencia"],  # type: ignore[arg-type]
            dimension=str(acumulado["dimension"]),
            tasa_desde=acumulado["tasa_desde"],  # type: ignore[arg-type]
            tasa_hasta_exclusiva=acumulado["tasa_hasta_exclusiva"],  # type: ignore[arg-type]
            numero_operaciones=int(acumulado["numero_operaciones"]),
            numero_operaciones_periodo_anterior=int(acumulado["numero_operaciones_periodo_anterior"]),
            numero_operaciones_mismo_rango_mes_anterior=int(acumulado["numero_operaciones_mismo_rango_mes_anterior"]),
            variacion_operaciones=(
                int(acumulado["numero_operaciones"])
                - int(acumulado["numero_operaciones_mismo_rango_mes_anterior"])
            ),
            monto_colocado=_monto(float(acumulado["monto_colocado"])),
            monto_colocado_periodo_anterior=_monto(float(acumulado["monto_colocado_periodo_anterior"])),
            monto_mismo_rango_mes_anterior=_monto(float(acumulado["monto_mismo_rango_mes_anterior"])),
            variacion_valor=_monto(
                float(acumulado["monto_colocado"])
                - float(acumulado["monto_mismo_rango_mes_anterior"])
            ),
        )
        for acumulado in sorted(
            agrupadas.values(),
            key=lambda fila: (str(fila["agencia"] or ""), _orden_dimension(str(fila["dimension"]))),
        )
    ]


def _etiqueta_dimension(valor: object) -> str:
    if valor is None:
        return "SIN DATOS"
    if isinstance(valor, int | float):
        return _formatear_tasa(float(valor))
    return str(valor).strip() or "SIN DATOS"


def _formatear_tasa(valor: float) -> str:
    return f"{valor:g}"


def _orden_dimension(valor: str) -> tuple[int, float | str]:
    try:
        return (0, float(valor.split("%", maxsplit=1)[0]))
    except ValueError:
        return (1, valor)


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
