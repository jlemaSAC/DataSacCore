from app.db.mongo import get_mongo_datasac_db_sync

from .repositories.mongo_control_diario_cartera_repository import MongoControlDiarioCarteraRepository
from .service import ControlDiarioCarteraService


def get_control_diario_cartera_service() -> ControlDiarioCarteraService:
    return ControlDiarioCarteraService(MongoControlDiarioCarteraRepository(get_mongo_datasac_db_sync()))
