from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.negocios.ahorro_restringido.control_diario_cancelacion.repositories.sql_cancelacion_restringidos_repository import (
    SqlCancelacionRestringidosRepository,
)
from app.modules.negocios.ahorro_restringido.control_diario_cancelacion.service import (
    ControlCancelacionRestringidosService,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)


def get_cancelacion_restringidos_service(
    db: Session = Depends(get_db),
) -> ControlCancelacionRestringidosService:
    return ControlCancelacionRestringidosService(
        SqlCancelacionRestringidosRepository(db), SqlSituacionCrediticiaAsesoresRepository(db),
    )
