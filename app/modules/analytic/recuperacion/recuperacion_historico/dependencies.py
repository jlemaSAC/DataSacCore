from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.mongo import get_mongo_datasac_db_sync
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.mongo_recuperacion_historico_repository import (
    MongoRecuperacionHistoricoRepository,
)
from app.modules.analytic.recuperacion.recuperacion_historico.service import RecuperacionHistoricoService
from app.modules.analytic.recuperacion.recuperacion_historico.repositories.sql_recuperacion_historico_repository import (
    SqlRecuperacionHistoricoRepository,
)


def get_recuperacion_historico_service(
    db: Session = Depends(get_db),
) -> RecuperacionHistoricoService:
    return RecuperacionHistoricoService(
        mongo_repository=MongoRecuperacionHistoricoRepository(get_mongo_datasac_db_sync()),
        sql_repository=SqlRecuperacionHistoricoRepository(db),
    )
