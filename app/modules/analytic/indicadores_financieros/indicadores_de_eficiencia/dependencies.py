from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.indicadores_financieros.indicadores_de_eficiencia.service import (
    IndicadoresDeEficienciaService,
)
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import (
    SqlSaldoContableRepository,
)


def get_indicadores_de_eficiencia_service(
    db: Session = Depends(get_db),
) -> IndicadoresDeEficienciaService:
    return IndicadoresDeEficienciaService(
        saldo_contable_repository=SqlSaldoContableRepository(db),
    )
