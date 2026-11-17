from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.evolucion_cuentas.cartera_por_vencer.service import (
    EvolucionCarteraPorVencerService,
    HistoricoCarteraPorVencerService,
)
from app.modules.contabilidad.repositories.sql_resumen_contable_repository import (
    SqlResumenContableRepository,
)


def get_evolucion_cartera_por_vencer_service(db: Session = Depends(get_db)) -> EvolucionCarteraPorVencerService:
    return EvolucionCarteraPorVencerService(SqlResumenContableRepository(db))


def get_historico_cartera_por_vencer_service(db: Session = Depends(get_db)) -> HistoricoCarteraPorVencerService:
    return HistoricoCarteraPorVencerService(SqlResumenContableRepository(db))
