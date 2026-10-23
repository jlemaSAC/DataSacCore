from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)
from app.modules.negocios.depositos_a_plazos.control_vencimiento.repositories.sql_control_vencimiento_repository import (
    SqlControlVencimientoRepository,
)
from app.modules.negocios.depositos_a_plazos.control_vencimiento.service import ControlVencimientoService


def get_control_vencimiento_service(db: Session = Depends(get_db)) -> ControlVencimientoService:
    return ControlVencimientoService(
        SqlControlVencimientoRepository(db), SqlSituacionCrediticiaAsesoresRepository(db),
    )
