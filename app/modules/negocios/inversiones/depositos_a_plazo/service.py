from datetime import date, datetime, timedelta

from fastapi import HTTPException

from app.modules.analytic.inversiones.repositories.sql_reporte_inversiones_repository import (
    SqlReporteInversionesRepository,
)
from app.modules.analytic.inversiones.schemas import ReporteInversionesFila
from app.modules.analytic.inversiones.service import ReporteInversionesService
from app.modules.auth.schemas import AuthContext
from app.modules.negocios.inversiones.depositos_a_plazo.schemas import (
    AgenciaResumenDepositos,
    IndicadoresDepositos,
    InputResumenActualDepositos,
    MetricasDepositos,
    ResumenActualDepositosResponse,
)


class ResumenActualDepositosService:
    def __init__(
        self,
        reporte_service: ReporteInversionesService,
        sql_repository: SqlReporteInversionesRepository,
    ) -> None:
        self.reporte_service = reporte_service
        self.sql_repository = sql_repository

    def obtener_resumen(
        self, body: InputResumenActualDepositos, auth: AuthContext
    ) -> ResumenActualDepositosResponse:
        fecha_sistema = auth.usuario.fecha_sistema
        if isinstance(fecha_sistema, datetime):
            fecha_sistema = fecha_sistema.date()
        if body.fecha_fin > fecha_sistema:
            raise HTTPException(400, "La fecha de corte no puede superar la fecha del sistema.")

        mes_anterior = body.fecha_fin.replace(day=1) - timedelta(days=1)
        anio_anterior = date(body.fecha_fin.year - 1, 12, 31)
        filas_por_fecha: dict[date, list[ReporteInversionesFila]] = {}
        # El corte seleccionado puede ser intramensual: nunca sustituirlo por
        # el cierre mensual de Mongo. El SP resuelve el último corte operativo.
        filas_por_fecha[body.fecha_fin] = [
            ReporteInversionesFila.model_validate(fila)
            for fila in self.sql_repository.obtener_corte_actual(body.fecha_fin)
        ]
        for fecha in dict.fromkeys([mes_anterior, anio_anterior]):
            reporte = self.reporte_service.obtener_por_rango(fecha, fecha, auth)
            filas_por_fecha[fecha] = reporte.filas

        # Una sola instantánea por fecha, incluso si la fuente contiene más
        # de un corte. Filtrar agencias después de determinar disponibilidad.
        cortes: dict[str, tuple[date | None, list[ReporteInversionesFila]]] = {}
        agencias_filtro = set(body.agencias)
        for nombre, fecha in (
            ("actual", body.fecha_fin),
            ("mes_anterior", mes_anterior),
            ("anio_anterior", anio_anterior),
        ):
            filas = filas_por_fecha[fecha]
            fechas = [
                _fecha_corte(fila) for fila in filas if _fecha_corte(fila) <= fecha
            ]
            corte_real = max(fechas, default=None)
            cortes[nombre] = (
                corte_real,
                [
                    fila for fila in filas
                    if _fecha_corte(fila) == corte_real
                    and (not agencias_filtro or fila.agencia.strip().upper() in agencias_filtro)
                ],
            )

        fecha_actual, filas_actuales = cortes["actual"]
        agencias = sorted({fila.agencia.strip().upper() for fila in filas_actuales} | agencias_filtro)
        return ResumenActualDepositosResponse(
            fecha_inicio=body.fecha_inicio,
            fecha_fin=body.fecha_fin,
            fecha_mes_anterior=mes_anterior,
            fecha_anio_anterior=anio_anterior,
            consolidado=not body.agencias,
            agencias=body.agencias,
            **{
                nombre: _resumir(
                    fecha, filas, body.fecha_inicio if nombre == "actual" else None
                )
                for nombre, (fecha, filas) in cortes.items()
            },
            por_agencia=[
                AgenciaResumenDepositos(
                    agencia=agencia,
                    **_metricas(
                        [fila for fila in filas_actuales if fila.agencia.strip().upper() == agencia],
                        body.fecha_inicio,
                        fecha_actual,
                    ).model_dump(),
                )
                for agencia in agencias
                if fecha_actual is not None
            ],
        )


def _fecha_corte(fila: ReporteInversionesFila) -> date:
    valor = fila.fecha_corte
    if len(valor) == 8:
        return datetime.strptime(valor, "%Y%m%d").date()
    return date.fromisoformat(valor)


def _tasa(filas: list[ReporteInversionesFila]) -> float | None:
    operaciones = sum(fila.operaciones for fila in filas)
    if not operaciones:
        return None
    return round(sum(fila.tasa_efectiva * fila.operaciones for fila in filas) / operaciones, 4)


def _resumir(
    fecha: date | None, filas: list[ReporteInversionesFila], fecha_inicio: date | None = None
) -> IndicadoresDepositos | None:
    if fecha is None:
        return None
    return IndicadoresDepositos(
        fecha_corte=fecha,
        **_metricas(filas, fecha_inicio or fecha.replace(day=1), fecha).model_dump(),
    )


def _metricas(
    filas: list[ReporteInversionesFila], fecha_inicio: date, fecha_fin: date
) -> MetricasDepositos:
    ingresados = [
        fila for fila in filas
        if fila.fecha_creacion is not None and fecha_inicio <= fila.fecha_creacion <= fecha_fin
    ]
    return MetricasDepositos(
        saldo=round(sum(fila.saldo for fila in filas), 2),
        numero_operaciones=sum(fila.operaciones for fila in filas),
        tasa_promedio=_tasa(filas),
        tasa_promedio_renovacion=_tasa(ingresados),
    )
