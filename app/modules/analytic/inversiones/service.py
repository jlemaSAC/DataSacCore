import calendar
import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from fastapi import HTTPException

from app.modules.analytic.inversiones.etl_client import (
    EtlReporteInversionesClient,
    EtlReporteInversionesError,
)
from app.modules.analytic.inversiones.repositories.mongo_reporte_inversiones_repository import (
    MongoReporteInversionesRepository,
)
from app.modules.analytic.inversiones.repositories.sql_reporte_inversiones_repository import (
    SqlReporteInversionesRepository,
)
from app.modules.analytic.inversiones.schemas import (
    CorteInversionesResponse,
    ReporteInversionesFila,
    ReporteInversionesRangoResponse,
)
from app.modules.auth.schemas import AuthContext


logger = logging.getLogger("uvicorn.error")


@dataclass(frozen=True)
class MesConsultado:
    periodo: str
    fecha_fin: date


class ReporteInversionesService:
    def __init__(
        self,
        mongo_repository: MongoReporteInversionesRepository,
        sql_repository: SqlReporteInversionesRepository,
        etl_client: EtlReporteInversionesClient,
    ) -> None:
        self.mongo_repository = mongo_repository
        self.sql_repository = sql_repository
        self.etl_client = etl_client

    def obtener_por_rango(
        self,
        fecha_desde: date,
        fecha_hasta: date,
        auth_context: AuthContext,
    ) -> ReporteInversionesRangoResponse:
        fecha_hoy = _fecha_sistema(auth_context)
        if fecha_hasta > fecha_hoy:
            raise HTTPException(status_code=400, detail="fecha_hasta no puede ser posterior a la fecha del sistema.")

        meses = _meses_del_rango(fecha_desde, fecha_hasta)

        self.mongo_repository.ensure_indexes()
        inicio_mes_actual = date(fecha_hoy.year, fecha_hoy.month, 1)
        meses_cerrados = [mes for mes in meses if mes.fecha_fin < inicio_mes_actual]
        periodos_cerrados = [mes.periodo for mes in meses_cerrados]
        periodos_cargados = self.mongo_repository.obtener_periodos_cargados(periodos_cerrados)

        origen_por_periodo: dict[
            str,
            Literal[
                "MONGO",
                "ETL_EN_DEMANDA",
                "SQL_EN_LINEA",
                "SIN_CORTE_DISPONIBLE",
            ],
        ] = {
            periodo: "MONGO" for periodo in periodos_cargados
        }
        for mes in meses_cerrados:
            if mes.periodo in periodos_cargados:
                continue
            origen = self._materializar_mes_faltante(mes)
            origen_por_periodo[mes.periodo] = origen

        filas_mongo = self.mongo_repository.obtener_filas(periodos_cerrados)
        filas = [ReporteInversionesFila.model_validate(fila) for fila in filas_mongo]

        if fecha_desde <= fecha_hoy <= fecha_hasta:
            filas.extend(
                ReporteInversionesFila.model_validate(fila)
                for fila in self.sql_repository.obtener_corte_actual(fecha_hoy)
            )
            origen_por_periodo[f"{fecha_hoy:%Y-%m}"] = "SQL_EN_LINEA"

        return _construir_respuesta(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            meses=meses,
            filas=filas,
            origen_por_periodo=origen_por_periodo,
        )

    def _materializar_mes_faltante(
        self,
        mes: MesConsultado,
    ) -> Literal["ETL_EN_DEMANDA", "SIN_CORTE_DISPONIBLE"]:
        try:
            self.etl_client.cargar_mes(mes.fecha_fin)
        except EtlReporteInversionesError as exc:
            logger.exception("Error materializando inversiones para %s", mes.periodo)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        if mes.periodo in self.mongo_repository.obtener_periodos_cargados([mes.periodo]):
            return "ETL_EN_DEMANDA"

        return "SIN_CORTE_DISPONIBLE"


def _fecha_sistema(auth_context: AuthContext) -> date:
    fecha_sistema = auth_context.usuario.fecha_sistema
    return fecha_sistema.date() if isinstance(fecha_sistema, datetime) else fecha_sistema


def _meses_del_rango(fecha_desde: date, fecha_hasta: date) -> list[MesConsultado]:
    meses: list[MesConsultado] = []
    cursor = date(fecha_desde.year, fecha_desde.month, 1)
    limite = date(fecha_hasta.year, fecha_hasta.month, 1)
    while cursor <= limite:
        ultimo_dia = calendar.monthrange(cursor.year, cursor.month)[1]
        meses.append(MesConsultado(f"{cursor:%Y-%m}", date(cursor.year, cursor.month, ultimo_dia)))
        cursor = date(cursor.year + (cursor.month == 12), (cursor.month % 12) + 1, 1)
    return meses


def _construir_respuesta(
    *,
    fecha_desde: date,
    fecha_hasta: date,
    meses: list[MesConsultado],
    filas: list[ReporteInversionesFila],
    origen_por_periodo: dict[str, str],
) -> ReporteInversionesRangoResponse:
    filas_por_periodo: dict[str, list[ReporteInversionesFila]] = {}
    for fila in filas:
        filas_por_periodo.setdefault(fila.periodo, []).append(fila)

    cortes: list[CorteInversionesResponse] = []
    for mes in meses:
        filas_mes = filas_por_periodo.get(mes.periodo, [])
        origen = origen_por_periodo.get(mes.periodo, "SIN_CORTE_DISPONIBLE")
        fecha_corte = max((fila.fecha_corte for fila in filas_mes), default=None)
        cortes.append(
            CorteInversionesResponse(
                periodo=mes.periodo,
                fecha_corte=fecha_corte,
                origen=origen,
                total_filas=len(filas_mes),
                operaciones=sum(fila.operaciones for fila in filas_mes),
                saldo=sum(fila.saldo for fila in filas_mes),
            )
        )

    return ReporteInversionesRangoResponse(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        total_operaciones=sum(fila.operaciones for fila in filas),
        total_saldo=sum(fila.saldo for fila in filas),
        cortes=cortes,
        filas=sorted(filas, key=lambda fila: (fila.fecha_corte, fila.agencia, fila.asesor)),
    )
