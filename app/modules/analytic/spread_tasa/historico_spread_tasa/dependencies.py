from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.spread_tasa.resumen_spread_tasa.repositories.sql_spread_agencias_repository import SqlSpreadAgenciasRepository
from .service import HistoricoSpreadTasaService


def get_historico_spread_tasa_service(db: Session = Depends(get_db)) -> HistoricoSpreadTasaService:
    return HistoricoSpreadTasaService(SqlSpreadAgenciasRepository(db))
