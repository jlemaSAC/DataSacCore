from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.db.session import get_db, get_secondary_session_factory
from app.modules.analytic.indicadores_financieros.solvencia.repositories.mongo_solvencia_repository import (
    MongoIndicadoresFinancierosRepository,
)
from app.modules.analytic.indicadores_financieros.solvencia.repositories.sql_solvencia_repository import (
    SqlIndicadoresFinancierosRepository,
)
from app.modules.analytic.indicadores_financieros.solvencia.service import (
    IndicadoresFinancierosService,
)
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import (
    SqlSaldoContableRepository,
)


def get_solvencia_service(
    db: Session = Depends(get_db),
) -> IndicadoresFinancierosService:
    return IndicadoresFinancierosService(
        saldo_contable_repository=SqlSaldoContableRepository(db),
        sql_repository=SqlIndicadoresFinancierosRepository(
            db=db,
            secondary_session_factory=get_secondary_session_factory(),
        ),
        mongo_repository=MongoIndicadoresFinancierosRepository(get_mongo_datasac_db_sync()),
    )
