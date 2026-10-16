from app.db.mongo import get_mongo_datasac_db_sync
from app.modules.negocios.recuperacion.castigo.repositories.mongo_castigo_repository import (
    MongoCastigoRepository,
)
from app.modules.negocios.recuperacion.castigo.service import CastigoService


def get_castigo_service() -> CastigoService:
    return CastigoService(
        mongo_repository=MongoCastigoRepository(get_mongo_datasac_db_sync())
    )
