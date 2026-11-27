from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.repositories.sql_auth_repository import SqlAuthRepository
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)

from .repositories.sql_control_cuentas_activas_repository import SqlControlCuentasActivasRepository
from .service import ControlCuentasActivasService


def get_control_cuentas_activas_service(
    db: Session = Depends(get_db),
) -> ControlCuentasActivasService:
    return ControlCuentasActivasService(
        SqlControlCuentasActivasRepository(db), SqlAuthRepository(db),
        SqlSituacionCrediticiaAsesoresRepository(db),
    )
