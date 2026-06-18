from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analytic.indicadores_financieros.calidad_de_activos.service import (
    IndicadoresCalidadDeActivosService,
)
from app.modules.contabilidad.repositories.sql_saldo_contable_repository import (
    SqlSaldoContableRepository,
)


def get_calidad_de_activos_service(
    db: Session = Depends(get_db),
) -> IndicadoresCalidadDeActivosService:
    return IndicadoresCalidadDeActivosService(
        saldo_contable_repository=SqlSaldoContableRepository(db),
    )
