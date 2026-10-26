from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.repositories.sql_control_diario_captaciones_repository import (
    SqlControlDiarioCaptacionesRepository,
)
from app.modules.negocios.depositos_a_plazos.control_diario_captaciones.service import ControlDiarioCaptacionesService


def get_control_diario_captaciones_service(db: Session = Depends(get_db)) -> ControlDiarioCaptacionesService:
    return ControlDiarioCaptacionesService(
        SqlControlDiarioCaptacionesRepository(db), SqlSituacionCrediticiaAsesoresRepository(db)
    )
