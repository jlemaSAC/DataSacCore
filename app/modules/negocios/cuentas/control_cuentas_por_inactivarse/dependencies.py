from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)

from .repositories.sql_control_cuentas_por_inactivarse_repository import SqlControlCuentasPorInactivarseRepository
from .service import ControlCuentasPorInactivarseService


def get_control_cuentas_por_inactivarse_service(
    db: Session = Depends(get_db),
) -> ControlCuentasPorInactivarseService:
    return ControlCuentasPorInactivarseService(
        SqlControlCuentasPorInactivarseRepository(db), SqlSituacionCrediticiaAsesoresRepository(db),
    )
