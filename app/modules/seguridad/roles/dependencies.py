from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.seguridad.roles.repositories.sql_rol_repository import SqlRolRepository
from app.modules.seguridad.roles.service import RolService


def get_rol_service(db: Session = Depends(get_db)) -> RolService:
    return RolService(repository=SqlRolRepository(db))
