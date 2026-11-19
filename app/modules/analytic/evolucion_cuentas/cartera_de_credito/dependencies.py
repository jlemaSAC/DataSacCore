from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.evolucion_cuentas.cartera_de_credito.service import (
    EvolucionCarteraService,
    HistoricoCarteraService,
)
from app.modules.contabilidad.repositories.sql_resumen_contable_repository import (
    SqlResumenContableRepository,
)


def get_evolucion_cartera_service(db: Session = Depends(get_db)) -> EvolucionCarteraService:
    return EvolucionCarteraService(SqlResumenContableRepository(db))


def get_historico_cartera_service(db: Session = Depends(get_db)) -> HistoricoCarteraService:
    return HistoricoCarteraService(SqlResumenContableRepository(db))
