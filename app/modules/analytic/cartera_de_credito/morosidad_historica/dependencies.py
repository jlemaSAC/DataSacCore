from app.db.mongo import get_mongo_datasac_db_sync
from app.modules.analytic.cartera_de_credito.morosidad_historica.repositories.mongo_morosidad_historica_repository import (
    MongoMorosidadHistoricaRepository,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.service import (
    MorosidadHistoricaService,
)


def get_morosidad_historica_service() -> MorosidadHistoricaService:
    return MorosidadHistoricaService(
        repository=MongoMorosidadHistoricaRepository(get_mongo_datasac_db_sync())
    )

