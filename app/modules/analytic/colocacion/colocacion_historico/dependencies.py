from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.db.session import get_db
from app.modules.analytic.colocacion.colocacion_historico.repositories.mongo_colocacion_historico_repository import (
    MongoColocacionHistoricoRepository,
)
from app.modules.analytic.colocacion.colocacion_historico.repositories.sql_colocacion_historico_repository import (
    SqlColocacionHistoricoRepository,
)
from app.modules.analytic.colocacion.colocacion_historico.service import (
    ColocacionHistoricoService,
)


def get_colocacion_historico_service(
    db: Session = Depends(get_db),
) -> ColocacionHistoricoService:
    return ColocacionHistoricoService(
        mongo_repository=MongoColocacionHistoricoRepository(get_mongo_datasac_db_sync()),
        sql_repository=SqlColocacionHistoricoRepository(db),
    )
