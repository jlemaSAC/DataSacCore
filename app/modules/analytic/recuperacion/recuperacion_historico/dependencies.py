from app.db.mongo import get_mongo_datasac_db_sync
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.mongo_recuperacion_historico_repository import (
    MongoRecuperacionHistoricoRepository,
)
from app.modules.analytic.recuperacion.recuperacion_historico.service import RecuperacionHistoricoService


def get_recuperacion_historico_service() -> RecuperacionHistoricoService:
    return RecuperacionHistoricoService(
        mongo_repository=MongoRecuperacionHistoricoRepository(get_mongo_datasac_db_sync())
    )
