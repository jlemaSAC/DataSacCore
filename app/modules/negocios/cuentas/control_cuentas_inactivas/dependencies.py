from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)

from .repositories.sql_control_cuentas_inactivas_repository import SqlControlCuentasInactivasRepository
from .service import ControlCuentasInactivasService


def get_control_cuentas_inactivas_service(
    db: Session = Depends(get_db),
) -> ControlCuentasInactivasService:
    return ControlCuentasInactivasService(
        SqlControlCuentasInactivasRepository(db), SqlSituacionCrediticiaAsesoresRepository(db),
    )
