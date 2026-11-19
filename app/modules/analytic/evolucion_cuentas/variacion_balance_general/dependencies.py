from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.modules.contabilidad.repositories.sql_resumen_contable_repository import SqlResumenContableRepository
from app.modules.analytic.evolucion_cuentas.variacion_balance_general.service import VariacionBalanceService


def get_variacion_balance_service(db: Session = Depends(get_db)) -> VariacionBalanceService:
    return VariacionBalanceService(SqlResumenContableRepository(db))
