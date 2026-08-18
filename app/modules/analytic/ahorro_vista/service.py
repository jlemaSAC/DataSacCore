from dataclasses import dataclass
from datetime import date, datetime

from fastapi import HTTPException

from app.modules.analytic.ahorro_vista.repositories.sql_reporte_ahorro_vista_repository import (
    SqlReporteAhorroVistaRepository,
)
from app.modules.analytic.ahorro_vista.schemas import (
    CorteAhorroVistaResponse,
    ReporteAhorroVistaFila,
    ReporteAhorroVistaRangoResponse,
)
from app.modules.auth.schemas import AuthContext


@dataclass(frozen=True)
class MesConsultado:
    periodo: str


class ReporteAhorroVistaService:
    def __init__(self, sql_repository: SqlReporteAhorroVistaRepository) -> None:
        self.sql_repository = sql_repository

    def obtener_por_rango(
        self,
        fecha_desde: date,
        fecha_hasta: date,
        auth_context: AuthContext,
    ) -> ReporteAhorroVistaRangoResponse:
        if fecha_hasta < fecha_desde:
            raise HTTPException(status_code=422, detail="fecha_hasta no puede ser menor que fecha_desde.")

        fecha_sistema = auth_context.usuario.fecha_sistema
        fecha_hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        if fecha_hasta > fecha_hoy:
            raise HTTPException(status_code=400, detail="fecha_hasta no puede ser posterior a la fecha del sistema.")

        filas = [
            ReporteAhorroVistaFila.model_validate(fila)
            for fila in self.sql_repository.obtener_por_rango(fecha_desde, fecha_hasta)
        ]
        meses = _meses_del_rango(fecha_desde, fecha_hasta)
        filas_por_periodo: dict[str, list[ReporteAhorroVistaFila]] = {}
        for fila in filas:
            filas_por_periodo.setdefault(fila.periodo, []).append(fila)

        cortes = [
            CorteAhorroVistaResponse(
                periodo=mes.periodo,
                fecha_corte=max((fila.fecha_corte for fila in filas_por_periodo.get(mes.periodo, [])), default=None),
                total_filas=len(filas_por_periodo.get(mes.periodo, [])),
                numero_transacciones_mes=sum(
                    fila.numero_transacciones_mes for fila in filas_por_periodo.get(mes.periodo, [])
                ),
                saldo=sum(fila.saldo for fila in filas_por_periodo.get(mes.periodo, [])),
            )
            for mes in meses
        ]
        return ReporteAhorroVistaRangoResponse(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            total_transacciones_mes=sum(fila.numero_transacciones_mes for fila in filas),
            total_saldo=sum(fila.saldo for fila in filas),
            cortes=cortes,
            filas=sorted(filas, key=lambda fila: (fila.fecha_corte, fila.agencia, fila.asesor)),
        )


def _meses_del_rango(fecha_desde: date, fecha_hasta: date) -> list[MesConsultado]:
    meses: list[MesConsultado] = []
    cursor = date(fecha_desde.year, fecha_desde.month, 1)
    limite = date(fecha_hasta.year, fecha_hasta.month, 1)
    while cursor <= limite:
        meses.append(MesConsultado(periodo=f"{cursor:%Y-%m}"))
        cursor = date(cursor.year + (cursor.month == 12), (cursor.month % 12) + 1, 1)
    return meses
