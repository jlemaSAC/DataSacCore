from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.db.redis import get_redis_cache_client
from app.db.session import get_db
from app.modules.analytic.cartera_de_credito.comparativo_cartera.repositories.sql_clientes_cartera_repository import (
    SqlClientesCarteraRepository,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.repositories.mongo_comparativo_cartera_repository import (
    MongoComparativoCarteraRepository,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.repositories.redis_comparativo_cartera_cache import (
    RedisComparativoCarteraCache,
)
from app.modules.analytic.cartera_de_credito.comparativo_cartera.service import (
    ComparativoCarteraService,
)


def get_comparativo_cartera_service(db: Session = Depends(get_db)) -> ComparativoCarteraService:
    return ComparativoCarteraService(
        repository=MongoComparativoCarteraRepository(get_mongo_datasac_db_sync()),
        cache=RedisComparativoCarteraCache(get_redis_cache_client()),
        clientes_repository=SqlClientesCarteraRepository(db),
    )
