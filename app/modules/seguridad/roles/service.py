from app.modules.auth.schemas import AuthContext
from app.modules.seguridad.roles.repositories.sql_rol_repository import SqlRolRepository
from app.modules.seguridad.roles.schemas import RolResponse


class RolService:
    def __init__(self, repository: SqlRolRepository) -> None:
        self.repository = repository

    def list_roles(
        self,
        auth_context: AuthContext,
        activo: bool | None = None,
    ) -> list[RolResponse]:
        _ = auth_context
        return [
            RolResponse.model_validate(rol)
            for rol in self.repository.list_roles(activo=activo)
        ]
