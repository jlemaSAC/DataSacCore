from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.recuperacion.recuperacion_historico.dependencies import (
    get_recuperacion_historico_service,
)
from app.modules.analytic.recuperacion.recuperacion_historico.service import (
    RecuperacionHistoricoService,
)
from app.modules.negocios.recuperacion.resumen.service import ResumenRecuperacionService
from app.modules.negocios.recuperacion.resumen.repositories.sql_detalle_recuperacion_repository import (
    SqlDetalleRecuperacionRepository,
)


def get_resumen_recuperacion_service(
    recuperacion_historico_service: RecuperacionHistoricoService = Depends(
        get_recuperacion_historico_service
    ),
) -> ResumenRecuperacionService:
    return ResumenRecuperacionService(recuperacion_historico_service)


def get_detalle_resumen_recuperacion_service(
    recuperacion_historico_service: RecuperacionHistoricoService = Depends(
        get_recuperacion_historico_service
    ),
    db: Session = Depends(get_db),
) -> ResumenRecuperacionService:
    return ResumenRecuperacionService(
        recuperacion_historico_service,
        SqlDetalleRecuperacionRepository(db),
    )
