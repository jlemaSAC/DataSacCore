from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.negocios.ahorro_vista.evaluacion_cuentas_ahorro_vista.repositories.sql_evaluacion_cuentas_ahorro_vista_repository import (
    SqlEvaluacionCuentasAhorroVistaRepository,
)
from app.modules.negocios.ahorro_vista.evaluacion_cuentas_ahorro_vista.service import (
    EvaluacionCuentasAhorroVistaService,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)


def get_evaluacion_cuentas_ahorro_vista_service(
    db: Session = Depends(get_db),
) -> EvaluacionCuentasAhorroVistaService:
    return EvaluacionCuentasAhorroVistaService(
        SqlEvaluacionCuentasAhorroVistaRepository(db), SqlSituacionCrediticiaAsesoresRepository(db),
    )
