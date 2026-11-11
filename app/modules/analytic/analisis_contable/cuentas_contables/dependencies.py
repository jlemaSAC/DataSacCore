from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.analisis_contable.cuentas_contables.repositories.sql_cuentas_contables_repository import SqlCuentasContablesRepository
from app.modules.analytic.analisis_contable.cuentas_contables.service import CuentasContablesService


def get_cuentas_contables_service(db: Session = Depends(get_db)) -> CuentasContablesService:
    return CuentasContablesService(SqlCuentasContablesRepository(db))
