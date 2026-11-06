from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.db.session import get_db
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.repositories.mongo_resumen_ahorro_vista_repository import (
    MongoResumenAhorroVistaRepository,
)
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.repositories.sql_resumen_ahorro_vista_repository import (
    SqlResumenAhorroVistaRepository,
)
from app.modules.negocios.ahorro_vista.resumen_ahorro_vista.service import ResumenAhorroVistaService


def get_resumen_ahorro_vista_service(db: Session = Depends(get_db)) -> ResumenAhorroVistaService:
    return ResumenAhorroVistaService(
        SqlResumenAhorroVistaRepository(db),
        MongoResumenAhorroVistaRepository(get_mongo_datasac_db_sync()),
    )
