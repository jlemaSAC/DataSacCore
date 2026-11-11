from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.repositories.sql_comparativa_cuentas_repository import SqlComparativaCuentasRepository
from app.modules.analytic.analisis_contable.comparativa_cuentas_contables.service import ComparativaCuentasService


def get_comparativa_cuentas_service(db: Session = Depends(get_db)) -> ComparativaCuentasService:
    return ComparativaCuentasService(SqlComparativaCuentasRepository(db))
