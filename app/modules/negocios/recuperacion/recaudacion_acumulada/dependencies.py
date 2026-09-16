from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.db.session import get_db
from app.modules.negocios.recuperacion.recaudacion_acumulada.repositories.mongo_recaudacion_acumulada_repository import (
    MongoRecaudacionAcumuladaRepository,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.repositories.sql_detalle_cuotas_repository import (
    SqlDetalleCuotasRepository,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.repositories.sql_asesores_agencia_repository import (
    SqlAsesoresAgenciaRepository,
)
from app.modules.negocios.recuperacion.recaudacion_acumulada.service import (
    AsesoresAgenciaService,
    RecaudacionAcumuladaService,
)


def get_recaudacion_acumulada_service(
    db: Session = Depends(get_db),
) -> RecaudacionAcumuladaService:
    return RecaudacionAcumuladaService(
        mongo_repository=MongoRecaudacionAcumuladaRepository(
            get_mongo_datasac_db_sync()
        ),
        sql_repository=SqlDetalleCuotasRepository(db),
    )


def get_asesores_agencia_service(
    db: Session = Depends(get_db),
) -> AsesoresAgenciaService:
    return AsesoresAgenciaService(SqlAsesoresAgenciaRepository(db))
