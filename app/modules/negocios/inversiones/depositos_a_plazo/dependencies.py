from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.inversiones.dependencies import get_reporte_inversiones_service
from app.modules.analytic.inversiones.repositories.sql_reporte_inversiones_repository import (
    SqlReporteInversionesRepository,
)
from app.modules.analytic.inversiones.service import ReporteInversionesService
from app.modules.negocios.inversiones.depositos_a_plazo.service import ResumenActualDepositosService


def get_resumen_actual_depositos_service(
    reporte: ReporteInversionesService = Depends(get_reporte_inversiones_service),
    db: Session = Depends(get_db),
) -> ResumenActualDepositosService:
    return ResumenActualDepositosService(reporte, SqlReporteInversionesRepository(db))
