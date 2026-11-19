from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.evolucion_cuentas.cartera_no_devenga.service import (
    EvolucionCarteraNoDevengaService,
    HistoricoCarteraNoDevengaService,
)
from app.modules.contabilidad.repositories.sql_resumen_contable_repository import (
    SqlResumenContableRepository,
)


def get_evolucion_cartera_no_devenga_service(db: Session = Depends(get_db)) -> EvolucionCarteraNoDevengaService:
    return EvolucionCarteraNoDevengaService(SqlResumenContableRepository(db))


def get_historico_cartera_no_devenga_service(db: Session = Depends(get_db)) -> HistoricoCarteraNoDevengaService:
    return HistoricoCarteraNoDevengaService(SqlResumenContableRepository(db))
