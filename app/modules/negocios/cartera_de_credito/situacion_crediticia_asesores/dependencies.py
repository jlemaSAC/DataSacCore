from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.db.session import get_db
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.mongo_situacion_crediticia_asesores_repository import (
    MongoSituacionCrediticiaAsesoresRepository,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.service import (
    SituacionCrediticiaAsesoresService,
)


def get_situacion_crediticia_asesores_service(
    db: Session = Depends(get_db),
) -> SituacionCrediticiaAsesoresService:
    return SituacionCrediticiaAsesoresService(
        mongo_repository=MongoSituacionCrediticiaAsesoresRepository(
            get_mongo_datasac_db_sync()
        ),
        sql_repository=SqlSituacionCrediticiaAsesoresRepository(db),
    )
