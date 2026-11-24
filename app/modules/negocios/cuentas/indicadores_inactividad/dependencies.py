from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

from .repositories.sql_indicadores_inactividad_repository import SqlIndicadoresInactividadRepository
from .service import IndicadoresInactividadService


def get_indicadores_inactividad_service(db: Session = Depends(get_db)) -> IndicadoresInactividadService:
    return IndicadoresInactividadService(SqlIndicadoresInactividadRepository(db))
