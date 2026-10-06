from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.recuperacion.recuperacion_historico.dependencies import (
    get_recuperacion_historico_service,
)
from app.modules.analytic.recuperacion.recuperacion_historico.service import (
    RecuperacionHistoricoService,
)
from app.modules.negocios.recuperacion.evaluacion_recuperacion.service import (
    EvaluacionRecuperacionService,
)
from app.modules.negocios.recuperacion.evaluacion_recuperacion.repositories.sql_detalle_recuperacion_repository import (
    SqlDetalleRecuperacionRepository,
)


def get_evaluacion_recuperacion_service(
    recuperacion_historico_service: RecuperacionHistoricoService = Depends(
        get_recuperacion_historico_service
    ),
) -> EvaluacionRecuperacionService:
    return EvaluacionRecuperacionService(recuperacion_historico_service)


def get_detalle_evaluacion_recuperacion_service(
    recuperacion_historico_service: RecuperacionHistoricoService = Depends(
        get_recuperacion_historico_service
    ),
    db: Session = Depends(get_db),
) -> EvaluacionRecuperacionService:
    return EvaluacionRecuperacionService(
        recuperacion_historico_service,
        SqlDetalleRecuperacionRepository(db),
    )
