from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)
from app.modules.negocios.depositos_a_plazos.evaluacion_captadores.repositories.sql_evaluacion_captadores_repository import (
    SqlEvaluacionCaptadoresRepository,
)
from app.modules.negocios.depositos_a_plazos.evaluacion_captadores.service import EvaluacionCaptadoresService


def get_evaluacion_captadores_service(db: Session = Depends(get_db)) -> EvaluacionCaptadoresService:
    return EvaluacionCaptadoresService(
        SqlEvaluacionCaptadoresRepository(db), SqlSituacionCrediticiaAsesoresRepository(db)
    )
