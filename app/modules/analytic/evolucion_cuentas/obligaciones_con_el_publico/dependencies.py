from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.evolucion_cuentas.obligaciones_con_el_publico.service import (
    EvolucionObligacionesConElPublicoService,
    HistoricoObligacionesConElPublicoService,
)
from app.modules.contabilidad.repositories.sql_resumen_contable_repository import (
    SqlResumenContableRepository,
)


def get_evolucion_obligaciones_con_el_publico_service(db: Session = Depends(get_db)) -> EvolucionObligacionesConElPublicoService:
    return EvolucionObligacionesConElPublicoService(SqlResumenContableRepository(db))


def get_historico_obligaciones_con_el_publico_service(db: Session = Depends(get_db)) -> HistoricoObligacionesConElPublicoService:
    return HistoricoObligacionesConElPublicoService(SqlResumenContableRepository(db))
