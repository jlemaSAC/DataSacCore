from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.db.session import get_db
from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.repositories.mongo_resumen_diario_cartera_repository import (
    MongoResumenDiarioCarteraRepository,
)
from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.repositories.sql_agencia_cartera_repository import (
    SqlAgenciaCarteraRepository,
)
from app.modules.negocios.cartera_de_credito.resumen_diario_asesores.service import (
    ResumenDiarioCarteraService,
)


def get_resumen_diario_cartera_service(
    db: Session = Depends(get_db),
) -> ResumenDiarioCarteraService:
    return ResumenDiarioCarteraService(
        sql_repository=SqlAgenciaCarteraRepository(db),
        mongo_repository=MongoResumenDiarioCarteraRepository(get_mongo_datasac_db_sync()),
    )
