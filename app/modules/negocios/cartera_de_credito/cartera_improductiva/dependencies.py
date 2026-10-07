from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.db.session import get_db
from app.modules.negocios.cartera_de_credito.cartera_improductiva.service import (
    CarteraImproductivaService,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.mongo_situacion_crediticia_asesores_repository import (
    MongoSituacionCrediticiaAsesoresRepository,
)
from app.modules.negocios.cartera_de_credito.situacion_crediticia_asesores.repositories.sql_situacion_crediticia_asesores_repository import (
    SqlSituacionCrediticiaAsesoresRepository,
)


def get_cartera_improductiva_service(
    db: Session = Depends(get_db),
) -> CarteraImproductivaService:
    return CarteraImproductivaService(
        mongo_repository=MongoSituacionCrediticiaAsesoresRepository(
            get_mongo_datasac_db_sync()
        ),
        sql_repository=SqlSituacionCrediticiaAsesoresRepository(db),
    )
