from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.indicadores_financieros.indicadores_de_liquidez.service import (
    IndicadoresDeLiquidezService,
)
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import (
    SqlSaldoContableRepository,
)


def get_indicadores_de_liquidez_service(
    db: Session = Depends(get_db),
) -> IndicadoresDeLiquidezService:
    return IndicadoresDeLiquidezService(
        saldo_contable_repository=SqlSaldoContableRepository(db),
    )
