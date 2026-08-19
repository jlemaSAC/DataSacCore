from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.settings import get_etl_settings
from app.db.mongo import get_mongo_datasac_db_sync
from app.db.session import get_db
from app.modules.analytic.ahorro_vista.etl_client import EtlReporteAhorroVistaClient
from app.modules.analytic.ahorro_vista.repositories.mongo_reporte_ahorro_vista_repository import (
    MongoReporteAhorroVistaRepository,
)
from app.modules.analytic.ahorro_vista.repositories.sql_reporte_ahorro_vista_repository import (
    SqlReporteAhorroVistaRepository,
)
from app.modules.analytic.ahorro_vista.service import ReporteAhorroVistaService


def get_reporte_ahorro_vista_service(
    db: Session = Depends(get_db),
) -> ReporteAhorroVistaService:
    etl_settings = get_etl_settings()
    return ReporteAhorroVistaService(
        sql_repository=SqlReporteAhorroVistaRepository(db),
        mongo_repository=MongoReporteAhorroVistaRepository(get_mongo_datasac_db_sync()),
        etl_client=EtlReporteAhorroVistaClient(
            etl_settings.base_url,
            etl_settings.timeout_seconds,
        ),
    )
