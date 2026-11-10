from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)
from app.modules.negocios.ahorro_restringido.control_vencimiento_restringido.repositories.sql_control_vencimiento_restringido_repository import (
    SqlControlVencimientoRestringidoRepository,
)
from app.modules.negocios.ahorro_restringido.control_vencimiento_restringido.service import ControlVencimientoRestringidoService


def get_control_vencimiento_restringido_service(db: Session = Depends(get_db)) -> ControlVencimientoRestringidoService:
    return ControlVencimientoRestringidoService(
        SqlControlVencimientoRestringidoRepository(db), SqlSituacionCrediticiaAsesoresRepository(db),
    )
