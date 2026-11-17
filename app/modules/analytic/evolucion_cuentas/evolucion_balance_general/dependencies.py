from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.evolucion_cuentas.evolucion_balance_general.service import EvolucionBalanceService
from app.modules.contabilidad.repositories.sql_resumen_contable_repository import SqlResumenContableRepository


def get_evolucion_balance_service(db: Session = Depends(get_db)) -> EvolucionBalanceService:
    return EvolucionBalanceService(SqlResumenContableRepository(db))
