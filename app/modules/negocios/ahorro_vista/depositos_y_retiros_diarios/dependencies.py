from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.negocios.ahorro_vista.depositos_y_retiros_diarios.repositories.sql_depositos_y_retiros_diarios_repository import (
    SqlDepositosYRetirosDiariosRepository,
)
from app.modules.negocios.ahorro_vista.depositos_y_retiros_diarios.service import (
    DepositosYRetirosDiariosService,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)


def get_depositos_y_retiros_diarios_service(
    db: Session = Depends(get_db),
) -> DepositosYRetirosDiariosService:
    return DepositosYRetirosDiariosService(
        SqlDepositosYRetirosDiariosRepository(db), SqlSituacionCrediticiaAsesoresRepository(db),
    )
