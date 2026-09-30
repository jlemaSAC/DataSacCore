from app.db.mongo import get_mongo_datasac_db_sync
from app.modules.negocios.cartera_de_credito.matriz_transicion.repositories.mongo_matriz_transicion_repository import (
    MongoMatrizTransicionRepository,
)
from app.modules.negocios.cartera_de_credito.matriz_transicion.service import MatrizTransicionService


def get_matriz_transicion_service() -> MatrizTransicionService:
    return MatrizTransicionService(
        mongo_repository=MongoMatrizTransicionRepository(get_mongo_datasac_db_sync()),
    )
