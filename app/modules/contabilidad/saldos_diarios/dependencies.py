from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.contabilidad.saldos_diarios.repositories.sql_saldos_diarios_repository import SqlSaldosDiariosRepository
from app.modules.contabilidad.saldos_diarios.service import SaldosDiariosService


def get_saldos_diarios_service(db: Session = Depends(get_db)) -> SaldosDiariosService:
    return SaldosDiariosService(SqlSaldosDiariosRepository(db))
