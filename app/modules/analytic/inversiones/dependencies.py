from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.settings import get_etl_settings
from app.db.mongo import get_mongo_datasac_db_sync
from app.db.session import get_db
from app.modules.analytic.inversiones.etl_client import EtlReporteInversionesClient
from app.modules.analytic.inversiones.repositories.mongo_reporte_inversiones_repository import (
    MongoReporteInversionesRepository,
)
from app.modules.analytic.inversiones.repositories.sql_reporte_inversiones_repository import (
    SqlReporteInversionesRepository,
)
from app.modules.analytic.inversiones.service import ReporteInversionesService


def get_reporte_inversiones_service(
    db: Session = Depends(get_db),
) -> ReporteInversionesService:
    etl_settings = get_etl_settings()
    return ReporteInversionesService(
        mongo_repository=MongoReporteInversionesRepository(get_mongo_datasac_db_sync()),
        sql_repository=SqlReporteInversionesRepository(db),
        etl_client=EtlReporteInversionesClient(
            etl_settings.base_url,
            etl_settings.timeout_seconds,
        ),
    )
