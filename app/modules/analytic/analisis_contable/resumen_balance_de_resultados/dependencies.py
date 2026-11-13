from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.contabilidad.repositories.sql_resumen_contable_repository import SqlResumenContableRepository
from app.modules.analytic.analisis_contable.resumen_balance_de_resultados.service import BalanceResultadosService


def get_balance_resultados_service(db: Session = Depends(get_db)) -> BalanceResultadosService:
    return BalanceResultadosService(SqlResumenContableRepository(db))
