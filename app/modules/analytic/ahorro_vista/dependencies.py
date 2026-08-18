from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.ahorro_vista.repositories.sql_reporte_ahorro_vista_repository import (
    SqlReporteAhorroVistaRepository,
)
from app.modules.analytic.ahorro_vista.service import ReporteAhorroVistaService


def get_reporte_ahorro_vista_service(
    db: Session = Depends(get_db),
) -> ReporteAhorroVistaService:
    return ReporteAhorroVistaService(SqlReporteAhorroVistaRepository(db))
