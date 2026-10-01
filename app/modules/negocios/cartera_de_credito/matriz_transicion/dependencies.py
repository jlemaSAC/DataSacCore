from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.db.session import get_db
from app.modules.negocios.cartera_de_credito.matriz_transicion.repositories.mongo_matriz_transicion_repository import (
    MongoMatrizTransicionRepository,
)
from app.modules.negocios.cartera_de_credito.matriz_transicion.service import MatrizTransicionService
from app.modules.negocios.recuperacion.recaudacion_acumulada.repositories.sql_detalle_cuotas_repository import (
    SqlDetalleCuotasRepository,
)


def get_matriz_transicion_service() -> MatrizTransicionService:
    return MatrizTransicionService(
        mongo_repository=MongoMatrizTransicionRepository(get_mongo_datasac_db_sync()),
    )


def get_matriz_transicion_prestamos_service(
    db: Session = Depends(get_db),
) -> MatrizTransicionService:
    return MatrizTransicionService(
        mongo_repository=MongoMatrizTransicionRepository(get_mongo_datasac_db_sync()),
        sql_repository=SqlDetalleCuotasRepository(db),
    )
