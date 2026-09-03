from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.negocios.colocacion.resumen.repositories.sql_colocacion_resumen_repository import (
    SqlColocacionResumenRepository,
)
from app.modules.negocios.colocacion.resumen.service import ResumenColocacionService


def get_resumen_colocacion_service(
    db: Session = Depends(get_db),
) -> ResumenColocacionService:
    return ResumenColocacionService(SqlColocacionResumenRepository(db))
