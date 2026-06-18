from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.indicadores_financieros.rentabilidad.service import (
    IndicadoresRentabilidadService,
)
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import (
    SqlSaldoContableRepository,
)


def get_rentabilidad_service(
    db: Session = Depends(get_db),
) -> IndicadoresRentabilidadService:
    return IndicadoresRentabilidadService(
        saldo_contable_repository=SqlSaldoContableRepository(db),
    )
