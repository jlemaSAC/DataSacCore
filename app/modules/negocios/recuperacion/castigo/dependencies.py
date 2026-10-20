from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.db.session import get_db
from app.modules.negocios.recuperacion.castigo.repositories.mongo_castigo_repository import (
    MongoCastigoRepository,
)
from app.modules.negocios.recuperacion.castigo.repositories.sql_castigo_repository import (
    SqlCastigoRepository,
)
from app.modules.negocios.recuperacion.castigo.service import CastigoService


def get_castigo_service(db: Session = Depends(get_db)) -> CastigoService:
    return CastigoService(
        mongo_repository=MongoCastigoRepository(get_mongo_datasac_db_sync()),
        sql_repository=SqlCastigoRepository(db),
    )
