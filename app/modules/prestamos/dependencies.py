from app.db.mongo import get_mongo_datasac_db_sync
from app.modules.prestamos.repositories.mongo_universo_repository import MongoUniversoPrestamosRepository
from app.modules.prestamos.service import UniversoPrestamosService


def get_universo_prestamos_service() -> UniversoPrestamosService:
    return UniversoPrestamosService(
        repository=MongoUniversoPrestamosRepository(get_mongo_datasac_db_sync()),
    )
