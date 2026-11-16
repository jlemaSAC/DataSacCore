from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.spread_tasa.resumen_spread_tasa.repositories.sql_spread_agencias_repository import SqlSpreadAgenciasRepository
from .service import CostoFondeoService


def get_costo_fondeo_service(db: Session = Depends(get_db)) -> CostoFondeoService:
    return CostoFondeoService(SqlSpreadAgenciasRepository(db))
