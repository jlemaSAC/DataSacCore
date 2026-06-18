from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.db.session import get_db
from app.modules.prestamos.repositories.mongo_universo_repository import MongoUniversoPrestamosRepository
from app.modules.prestamos.repositories.sql_universo_repository import SqlUniversoPrestamosRepository
from app.modules.prestamos.service import UniversoPrestamosService


def get_universo_prestamos_service(db: Session = Depends(get_db)) -> UniversoPrestamosService:
    return UniversoPrestamosService(
        repository=MongoUniversoPrestamosRepository(get_mongo_datasac_db_sync()),
        sql_repository=SqlUniversoPrestamosRepository(db),
    )
