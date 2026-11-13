from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.contabilidad.repositories.sql_resumen_contable_repository import SqlResumenContableRepository
from app.modules.analytic.analisis_contable.cuentas_contables.service import CuentasContablesService


def get_cuentas_contables_service(db: Session = Depends(get_db)) -> CuentasContablesService:
    return CuentasContablesService(SqlResumenContableRepository(db))
