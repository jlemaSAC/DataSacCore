from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)
from app.modules.negocios.depositos_a_plazos.control_diario_cancelacion.repositories.sql_control_diario_cancelacion_repository import (
    SqlControlDiarioCancelacionRepository,
)
from app.modules.negocios.depositos_a_plazos.control_diario_cancelacion.service import ControlDiarioCancelacionService


def get_control_diario_cancelacion_service(db: Session = Depends(get_db)) -> ControlDiarioCancelacionService:
    return ControlDiarioCancelacionService(
        SqlControlDiarioCancelacionRepository(db), SqlSituacionCrediticiaAsesoresRepository(db)
    )
