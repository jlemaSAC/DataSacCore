from datetime import datetime
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
    UniversoPrestamosBuscarResponse,
    UniversoPrestamosConteos,
)


TIMEZONE_ECUADOR = ZoneInfo("America/Guayaquil")


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

        if request.crear_indices:
            self.repository.ensure_actual_indexes()

        rows = self.sql_repository.get_prestamos_actuales(limit=request.limit)
        snapshots = [prestamo_snapshot_from_sql_row(row) for row in rows]
        write_result = self.repository.upsert_actual_snapshots(
            snapshots,
            as_of=as_of,
            data_version=data_version,
        )

        return SituacionCrediticiaActualSyncResponse(
            collection=SITUACION_CREDITICIA_ACTUAL_COLLECTION,
            data_version=data_version,
            as_of=as_of,
            total_leidos_sql=len(rows),
            total_upserted=write_result["upserted"],
            total_matched=write_result["matched"],
            total_modified=write_result["modified"],
        )
