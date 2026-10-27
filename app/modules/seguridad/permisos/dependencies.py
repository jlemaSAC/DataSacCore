from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_app_web_menu_db_sync
from app.db.session import get_db
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.service import AuthService
from app.modules.seguridad.permisos.repositories.mongo_permiso_repository import MongoPermisoRepository
from app.modules.seguridad.permisos.service import PermisoService
from app.modules.seguridad.roles.repositories.sql_rol_repository import SqlRolRepository


def get_permiso_service(db: Session = Depends(get_db), auth: AuthService = Depends(get_auth_service)) -> PermisoService:
    return PermisoService(
        repository=MongoPermisoRepository(get_mongo_datasac_app_web_menu_db_sync()),
        roles=SqlRolRepository(db), auth=auth,
    )
