from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.auth.repositories.sql_auth_repository import SqlAuthRepository
from app.modules.auth.schemas import AuthContext
from app.modules.analytic.menu.repositories.mongo_menu_repository import (
    MongoMenuAnalyticAdminRepository,
)
from app.modules.analytic.menu.schemas import (
    MenuAnalyticAdminResponse,
    MenuAnalyticAdminTreeResponse,
    MenuAnalyticCreateRequest,
    MenuAnalyticDeleteResponse,
    MenuAnalyticResponse,
    MenuAnalyticUpdateRequest,
    PermisoAnalyticAdminResponse,
    PermisoAnalyticCreateRequest,
    RolPermisoAnalyticAdminResponse,
    RolPermisoAnalyticCreateRequest,
)


class MenuAnalyticAdminService:
    admin_role_code = "001"

    def __init__(
        self,
        db: Session,
        repository: MongoMenuAnalyticAdminRepository,
        sql_repository: SqlAuthRepository | None = None,
    ) -> None:
        self.db = db
        self.repository = repository
        self.sql_repository = sql_repository or SqlAuthRepository(db)

    def get_menu(
        self,
        auth_context: AuthContext,
    ) -> list[MenuAnalyticResponse]:
        roles_codigo = [
            rol.codigo
            for rol in self.sql_repository.get_roles_usuario(auth_context.usuario.sub)
        ]
        return self.repository.get_menu_by_roles(roles_codigo)

    def list_menu_routes(
        self,
        auth_context: AuthContext,
        activo: bool | None = None,
    ) -> list[MenuAnalyticAdminResponse]:
        self._validate_admin_user(auth_context)
        return self.repository.list_menu_routes(activo=activo)

    def create_menu_route(
        self,
        auth_context: AuthContext,
        data: MenuAnalyticCreateRequest,
    ) -> MenuAnalyticAdminResponse:
        self._validate_admin_user(auth_context)
        roles_codigo = self._normalizar_roles_codigo(data.roles_codigo)
        for rol_codigo in roles_codigo:
            self._validar_rol_destino(rol_codigo)
        return self.repository.create_menu_route(
            data.model_copy(update={"roles_codigo": roles_codigo})
        )

    def list_menu_tree(
        self,
        auth_context: AuthContext,
        activo: bool | None = None,
    ) -> list[MenuAnalyticAdminTreeResponse]:
        self._validate_admin_user(auth_context)
        return self.repository.list_menu_tree(activo=activo)

    def get_menu_route(
        self,
        auth_context: AuthContext,
        id_menu: str,
    ) -> MenuAnalyticAdminResponse:
        self._validate_admin_user(auth_context)
        return self.repository.get_menu_route(id_menu)

    def update_menu_route(
        self,
        auth_context: AuthContext,
        id_menu: str,
        data: MenuAnalyticUpdateRequest,
    ) -> MenuAnalyticAdminResponse:
        self._validate_admin_user(auth_context)
        if data.roles_codigo is not None:
            roles_codigo = self._normalizar_roles_codigo(data.roles_codigo)
            for rol_codigo in roles_codigo:
                self._validar_rol_destino(rol_codigo)
            data = data.model_copy(update={"roles_codigo": roles_codigo})
        return self.repository.update_menu_route(id_menu, data)

    def delete_menu_route(
        self,
        auth_context: AuthContext,
        id_menu: str,
    ) -> MenuAnalyticDeleteResponse:
        self._validate_admin_user(auth_context)
        return self.repository.delete_menu_route(id_menu)

    def create_permission(
        self,
        auth_context: AuthContext,
        data: PermisoAnalyticCreateRequest,
    ) -> PermisoAnalyticAdminResponse:
        self._validate_admin_user(auth_context)
        return self.repository.create_permission(data)

    def create_role_permission(
        self,
        auth_context: AuthContext,
        data: RolPermisoAnalyticCreateRequest,
    ) -> RolPermisoAnalyticAdminResponse:
        self._validate_admin_user(auth_context)
        self._validar_rol_destino(data.rol_codigo)
        return self.repository.create_role_permission(data)

    def _validate_admin_user(self, auth_context: AuthContext) -> None:
        roles_usuario = self.sql_repository.get_roles_usuario(auth_context.usuario.sub)
        tiene_rol_admin = any(rol.codigo == self.admin_role_code for rol in roles_usuario)
        if not tiene_rol_admin:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para administrar el menu Analytic Sac.",
            )

    def _validar_rol_destino(self, rol_codigo: str) -> None:
        rol_codigo = rol_codigo.strip()
        if not rol_codigo:
            raise HTTPException(status_code=400, detail="El rol es obligatorio.")

        rol = self.sql_repository.get_rol_activo(rol_codigo)
        if rol is None:
            raise HTTPException(status_code=404, detail="Rol no encontrado o inactivo.")

    def _normalizar_roles_codigo(self, roles_codigo: list[str]) -> list[str]:
        roles = [
            rol.strip()
            for rol in roles_codigo
            if isinstance(rol, str) and rol.strip()
        ]
        if not roles:
            return [self.admin_role_code]
        return list(dict.fromkeys(roles))
