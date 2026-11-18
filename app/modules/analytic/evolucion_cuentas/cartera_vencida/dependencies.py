from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.evolucion_cuentas.cartera_vencida.service import (
    EvolucionCarteraVencidaService,
    HistoricoCarteraVencidaService,
)
from app.modules.contabilidad.repositories.sql_resumen_contable_repository import (
    SqlResumenContableRepository,
)


def get_evolucion_cartera_vencida_service(db: Session = Depends(get_db)) -> EvolucionCarteraVencidaService:
    return EvolucionCarteraVencidaService(SqlResumenContableRepository(db))


def get_historico_cartera_vencida_service(db: Session = Depends(get_db)) -> HistoricoCarteraVencidaService:
    return HistoricoCarteraVencidaService(SqlResumenContableRepository(db))
