from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.evolucion_cuentas.balance_de_resultados.service import (
    EvolucionResultadosService,
    VariacionResultadosService,
)
from app.modules.contabilidad.repositories.sql_resumen_contable_repository import (
    SqlResumenContableRepository,
)


def get_evolucion_resultados_service(db: Session = Depends(get_db)) -> EvolucionResultadosService:
    return EvolucionResultadosService(SqlResumenContableRepository(db))


def get_variacion_resultados_service(db: Session = Depends(get_db)) -> VariacionResultadosService:
    return VariacionResultadosService(SqlResumenContableRepository(db))
