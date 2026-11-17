from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.spread_tasa.resumen_spread_tasa.service import ResumenSpreadTasaService
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import SqlSaldoContableRepository
from app.modules.analytic.spread_tasa.resumen_spread_tasa.repositories.sql_spread_agencias_repository import SqlSpreadAgenciasRepository


def get_resumen_spread_tasa_service(db: Session = Depends(get_db)) -> ResumenSpreadTasaService:
    return ResumenSpreadTasaService(SqlSaldoContableRepository(db), SqlSpreadAgenciasRepository(db))
