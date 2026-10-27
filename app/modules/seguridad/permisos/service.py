from fastapi import HTTPException

from app.modules.auth.schemas import AuthContext
from app.modules.auth.service import AuthService
from app.modules.seguridad.permisos.repositories.mongo_permiso_repository import MongoPermisoRepository
from app.modules.seguridad.permisos.schemas import AccessBatchRequest, AccessBatchResponse, AccessStateResponse
from app.modules.seguridad.roles.repositories.sql_rol_repository import SqlRolRepository
from app.modules.seguridad.roles.schemas import RolResponse


class PermisoService:
    def __init__(self, repository: MongoPermisoRepository, roles: SqlRolRepository, auth: AuthService) -> None:
        self.repository = repository
        self.roles = roles
        self.auth = auth

    def get_state(self, context: AuthContext) -> AccessStateResponse:
        self.auth.validate_menu_admin(context.usuario.sub)
        cargos = [RolResponse.model_validate(role) for role in self.roles.list_roles()]
        snapshot = self.repository.get_snapshot()
        return AccessStateResponse(**snapshot.model_dump(), cargos=cargos)

    def save(self, context: AuthContext, data: AccessBatchRequest) -> AccessBatchResponse:
        self.auth.validate_menu_admin(context.usuario.sub)
        cargos = [RolResponse.model_validate(role) for role in self.roles.list_roles()]
        by_code = {role.codigo: role for role in cargos}
        seen: set[tuple[str, str]] = set()
        for change in data.cambios:
            key = (change.menu_id, change.rol_codigo)
            if key in seen:
                raise HTTPException(status_code=400, detail="Asignación repetida dentro del lote.")
            seen.add(key)
            role = by_code.get(change.rol_codigo)
            if role is None or (change.conceder and not role.activo):
                raise HTTPException(status_code=404, detail=f"Cargo/rol {change.rol_codigo} inexistente o inactivo para conceder acceso.")
        snapshot, count = self.repository.apply_batch(data)
        return AccessBatchResponse(**snapshot.model_dump(), cargos=cargos, modificaciones=count)
