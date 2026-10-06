from app.db.mongo import get_mongo_datasac_db_sync
from app.modules.negocios.recuperacion.resumen_recuperacion.repositories.mongo_resumen_recuperacion_repository import (
    MongoResumenRecuperacionRepository,
)
from app.modules.negocios.recuperacion.resumen_recuperacion.service import (
    ResumenRecuperacionService,
)


def get_resumen_recuperacion_service() -> ResumenRecuperacionService:
    return ResumenRecuperacionService(
        MongoResumenRecuperacionRepository(get_mongo_datasac_db_sync())
    )
