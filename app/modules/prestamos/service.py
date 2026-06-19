from datetime import datetime
from time import perf_counter
from zoneinfo import ZoneInfo

from app.modules.auth.schemas import AuthContext
from app.modules.prestamos.constants import SITUACION_CREDITICIA_ACTUAL_COLLECTION
from app.modules.prestamos.mappers import prestamo_snapshot_from_sql_row
from app.modules.prestamos.repositories.mongo_universo_repository import MongoUniversoPrestamosRepository
from app.modules.prestamos.repositories.sql_universo_repository import SqlUniversoPrestamosRepository
from app.modules.prestamos.schemas import (
    PrestamoUniverseRequest,
    SituacionCrediticiaActualSyncRequest,
    SituacionCrediticiaActualSyncResponse,
    SituacionCrediticiaActualSyncTimings,
    UniversoPrestamosBuscarResponse,
    UniversoPrestamosConteos,
)


TIMEZONE_ECUADOR = ZoneInfo("America/Guayaquil")


def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000, 2)


class UniversoPrestamosService:
    def __init__(
        self,
        repository: MongoUniversoPrestamosRepository | None = None,
        sql_repository: SqlUniversoPrestamosRepository | None = None,
    ) -> None:
        self.repository = repository
        self.sql_repository = sql_repository

    def buscar_universo(
        self,
        filtros: PrestamoUniverseRequest,
        auth_context: AuthContext,
    ) -> UniversoPrestamosBuscarResponse:
        _ = auth_context
        if self.repository is None:
            raise RuntimeError("Repositorio Mongo de universo de prestamos no configurado.")

        actual = self.repository.get_actual_snapshots(filtros)
        historico = self.repository.get_historico_snapshots(filtros)

        return UniversoPrestamosBuscarResponse(
            actual=actual,
            historico=historico,
            conteos=UniversoPrestamosConteos(
                actual=len(actual),
                historico=len(historico),
            ),
        )

    def sincronizar_situacion_crediticia_actual(
        self,
        request: SituacionCrediticiaActualSyncRequest,
        auth_context: AuthContext,
    ) -> SituacionCrediticiaActualSyncResponse:
        _ = auth_context
        if self.repository is None:
            raise RuntimeError("Repositorio Mongo de universo de prestamos no configurado.")
        if self.sql_repository is None:
            raise RuntimeError("Repositorio SQL de universo de prestamos no configurado.")

        as_of = datetime.now(TIMEZONE_ECUADOR)
        data_version = as_of.strftime("%Y%m%d-%H%M%S")

        total_start = perf_counter()

        ensure_indexes_start = perf_counter()
        self.repository.ensure_actual_indexes()
        ensure_indexes_ms = _elapsed_ms(ensure_indexes_start)

        sql_read_start = perf_counter()
        rows = self.sql_repository.get_prestamos_actuales(limit=request.limit)
        sql_read_ms = _elapsed_ms(sql_read_start)

        python_map_start = perf_counter()
        snapshots = [prestamo_snapshot_from_sql_row(row) for row in rows]
        python_map_ms = _elapsed_ms(python_map_start)

        mongo_upsert_start = perf_counter()
        write_result = self.repository.upsert_actual_snapshots(
            snapshots,
            as_of=as_of,
            data_version=data_version,
        )
        mongo_upsert_ms = _elapsed_ms(mongo_upsert_start)

        return SituacionCrediticiaActualSyncResponse(
            collection=SITUACION_CREDITICIA_ACTUAL_COLLECTION,
            data_version=data_version,
            as_of=as_of,
            total_leidos_sql=len(rows),
            total_upserted=write_result["upserted"],
            total_matched=write_result["matched"],
            total_modified=write_result["modified"],
            timings_ms=SituacionCrediticiaActualSyncTimings(
                ensure_indexes_ms=ensure_indexes_ms,
                sql_read_ms=sql_read_ms,
                python_map_ms=python_map_ms,
                mongo_upsert_ms=mongo_upsert_ms,
                total_ms=_elapsed_ms(total_start),
            ),
        )
