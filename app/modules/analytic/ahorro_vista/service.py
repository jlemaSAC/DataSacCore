from dataclasses import dataclass
from datetime import date, datetime, timedelta

from fastapi import HTTPException

from app.modules.analytic.ahorro_vista.etl_client import (
    EtlReporteAhorroVistaClient,
    EtlReporteAhorroVistaError,
)
from app.modules.analytic.ahorro_vista.repositories.mongo_reporte_ahorro_vista_repository import (
    MongoReporteAhorroVistaRepository,
)
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
    def __init__(
        self,
        sql_repository: SqlReporteAhorroVistaRepository,
        mongo_repository: MongoReporteAhorroVistaRepository,
        etl_client: EtlReporteAhorroVistaClient,
    ) -> None:
        self.sql_repository = sql_repository
        self.mongo_repository = mongo_repository
        self.etl_client = etl_client

    def obtener_por_rango(
        self,
        fecha_desde: date,
        fecha_hasta: date,
        auth_context: AuthContext,
        es_programado: bool | None = None,
    ) -> ReporteAhorroVistaRangoResponse:
        if fecha_hasta < fecha_desde:
            raise HTTPException(status_code=422, detail="fecha_hasta no puede ser menor que fecha_desde.")

        fecha_sistema = auth_context.usuario.fecha_sistema
        fecha_hoy = fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema
        if fecha_hasta > fecha_hoy:
            raise HTTPException(status_code=400, detail="fecha_hasta no puede ser posterior a la fecha del sistema.")

        meses = _meses_del_rango(fecha_desde, fecha_hasta)
        filas: list[ReporteAhorroVistaFila] = []
        for mes in meses:
            fecha_mes = date.fromisoformat(f"{mes.periodo}-01")
            if mes.periodo == f"{fecha_hoy:%Y-%m}":
                filas_origen = self.sql_repository.obtener_por_rango(
                    fecha_hoy,
                    fecha_hoy,
                    es_programado,
                )
            else:
                if not self.mongo_repository.existe_corte_mensual(fecha_mes, es_programado):
                    self._materializar_mes_faltante(fecha_mes, es_programado)
                filas_origen = self.mongo_repository.obtener_por_mes(fecha_mes, es_programado)
            filas.extend(ReporteAhorroVistaFila.model_validate(fila) for fila in filas_origen)
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

    def _materializar_mes_faltante(
        self,
        fecha_inicio: date,
        es_programado: bool | None,
    ) -> None:
        try:
            self.etl_client.cargar_mes(
                fecha_inicio,
                _ultimo_dia_mes(fecha_inicio),
                es_programado,
            )
        except EtlReporteAhorroVistaError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc


def _meses_del_rango(fecha_desde: date, fecha_hasta: date) -> list[MesConsultado]:
    meses: list[MesConsultado] = []
    cursor = date(fecha_desde.year, fecha_desde.month, 1)
    limite = date(fecha_hasta.year, fecha_hasta.month, 1)
    while cursor <= limite:
        meses.append(MesConsultado(periodo=f"{cursor:%Y-%m}"))
        cursor = date(cursor.year + (cursor.month == 12), (cursor.month % 12) + 1, 1)
    return meses


def _ultimo_dia_mes(mes: date) -> date:
    return date(mes.year + (mes.month == 12), (mes.month % 12) + 1, 1) - timedelta(days=1)
