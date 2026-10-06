from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.negocios.colocacion.diaria_asesores.repositories.sql_colocacion_diaria_asesores_repository import (
    SqlColocacionDiariaAsesoresRepository,
)
from app.modules.negocios.colocacion.diaria_asesores.service import (
    ColocacionDiariaAsesoresService,
)


def get_colocacion_diaria_asesores_service(
    db: Session = Depends(get_db),
) -> ColocacionDiariaAsesoresService:
    return ColocacionDiariaAsesoresService(SqlColocacionDiariaAsesoresRepository(db))
