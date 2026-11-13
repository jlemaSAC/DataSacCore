from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.contabilidad.repositories.sql_resumen_contable_repository import SqlResumenContableRepository
from app.modules.analytic.analisis_contable.resumen_resultados_del_ejercicio.service import ResultadosEjercicioService


def get_resultados_ejercicio_service(db: Session = Depends(get_db)) -> ResultadosEjercicioService:
    return ResultadosEjercicioService(SqlResumenContableRepository(db))
