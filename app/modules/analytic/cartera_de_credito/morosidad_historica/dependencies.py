from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.db.redis import get_redis_cache_client
from app.db.session import get_db
from app.modules.analytic.cartera_de_credito.morosidad_historica.repositories.mongo_morosidad_historica_repository import (
    MongoMorosidadHistoricaRepository,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.repositories.redis_morosidad_historica_cache import (
    RedisMorosidadHistoricaCache,
)
from app.modules.analytic.cartera_de_credito.morosidad_historica.service import (
    MorosidadHistoricaCacheAdminService,
    MorosidadHistoricaService,
)
from app.modules.auth.repositories.sql_auth_repository import SqlAuthRepository


def get_morosidad_historica_service() -> MorosidadHistoricaService:
    return MorosidadHistoricaService(
        repository=MongoMorosidadHistoricaRepository(get_mongo_datasac_db_sync()),
        cache=RedisMorosidadHistoricaCache(get_redis_cache_client()),
    )


def get_morosidad_historica_cache_admin_service(
    db: Session = Depends(get_db),
) -> MorosidadHistoricaCacheAdminService:
    return MorosidadHistoricaCacheAdminService(
        cache=RedisMorosidadHistoricaCache(get_redis_cache_client()),
        sql_repository=SqlAuthRepository(db),
    )
