from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.evolucion_cuentas.depositos_a_plazos.service import (
    EvolucionDepositosAPlazosService,
    VariacionDepositosAPlazosService,
)
from app.modules.contabilidad.repositories.sql_resumen_contable_repository import (
    SqlResumenContableRepository,
)


def get_evolucion_depositos_a_plazos_service(db: Session = Depends(get_db)) -> EvolucionDepositosAPlazosService:
    return EvolucionDepositosAPlazosService(SqlResumenContableRepository(db))


def get_variacion_depositos_a_plazos_service(db: Session = Depends(get_db)) -> VariacionDepositosAPlazosService:
    return VariacionDepositosAPlazosService(SqlResumenContableRepository(db))
