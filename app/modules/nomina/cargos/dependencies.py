from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.nomina.cargos.repositories.sql_cargo_repository import SqlCargoRepository
from app.modules.nomina.cargos.service import CargoService


def get_cargo_service(db: Session = Depends(get_db)) -> CargoService:
    return CargoService(repository=SqlCargoRepository(db))
