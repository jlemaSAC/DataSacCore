from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_app_web_menu_db_sync
from app.modules.auth.repositories.mongo_menu_repository import MongoMenuRepository
from app.modules.auth.repositories.sql_auth_repository import SqlAuthRepository
from app.modules.auth.schemas import (
    LoginResponse,
    MenuAdminChild,
    MenuChild,
    MenuCompleteResponse,
    MenuDataSacWebCreateRequest,
    MenuDataSacWebDeleteResponse,
    MenuDataSacWebUpdateRequest,
    MenuResponse,
    OficinaConsultaItem,
    RolOut,
    UserLogin,
)
from app.modules.auth.security import JwtTokenService, PasswordHasher


class AuthService:
    validar_fecha_sistema_en_login = False
    admin_role_code = "001"

    def __init__(
        self,
        db: Session,
        sql_repository: SqlAuthRepository | None = None,
        menu_repository: MongoMenuRepository | None = None,
        password_hasher: PasswordHasher | None = None,
        token_service: JwtTokenService | None = None,
    ) -> None:
        self.db = db
        self.sql_repository = sql_repository or SqlAuthRepository(db)
        self.menu_repository = menu_repository
        self.password_hasher = password_hasher or PasswordHasher()
        self.token_service = token_service or JwtTokenService()

    def login(self, login_data: UserLogin) -> LoginResponse:
        try:
            response = self._authenticate_user(login_data)
        except HTTPException:
            self.db.rollback()
            raise
        except Exception:
            self.db.rollback()
            raise

        return response

    def build_menu_response(self, codigo_usuario: str) -> MenuResponse:
        usuario = self._get_enabled_user(codigo_usuario)

        roles_out = self._get_roles_out(usuario.usuario)
        menu = self._get_menu_for_roles(roles_out)
        return MenuResponse(menu=menu)

    def build_complete_menu_response(
        self,
        codigo_usuario: str,
        activo: bool | None = None,
    ) -> MenuCompleteResponse:
        self._validate_menu_admin(codigo_usuario)

        return MenuCompleteResponse(menu=self._get_menu_repository().get_complete_menu_tree(activo=activo))

    def create_data_sac_web_menu_node(
        self,
        codigo_usuario: str,
        data: MenuDataSacWebCreateRequest,
    ) -> MenuAdminChild:
        self._validate_menu_admin(codigo_usuario)
        roles = self._validate_target_roles(data.roles_codigo)
        return self._get_menu_repository().create_menu_node(data.model_copy(update={"roles_codigo": roles}))

    def update_data_sac_web_menu_node(
        self,
        codigo_usuario: str,
        id_menu: str,
        data: MenuDataSacWebUpdateRequest,
    ) -> MenuAdminChild:
        self._validate_menu_admin(codigo_usuario)
        if data.roles_codigo is not None:
            roles = self._validate_target_roles(data.roles_codigo)
            data = data.model_copy(update={"roles_codigo": roles})
        return self._get_menu_repository().update_menu_node(id_menu, data)

    def get_data_sac_web_menu_node(self, codigo_usuario: str, id_menu: str) -> MenuAdminChild:
        self._validate_menu_admin(codigo_usuario)
        return self._get_menu_repository().get_menu_node(id_menu)

    def delete_data_sac_web_menu_node(
        self,
        codigo_usuario: str,
        id_menu: str,
    ) -> MenuDataSacWebDeleteResponse:
        self._validate_menu_admin(codigo_usuario)
        permission = self._get_menu_repository().delete_menu_node(id_menu)
        return MenuDataSacWebDeleteResponse(
            id=id_menu,
            permiso_codigo=permission,
            detail="Menu, permiso y asignaciones de rol eliminados correctamente.",
        )

    def _authenticate_user(self, login_data: UserLogin) -> LoginResponse:
        usuario_data = self.sql_repository.get_usuario_login_data(login_data.codigo)
        if usuario_data is None:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        if not usuario_data.activo:
            raise HTTPException(status_code=403, detail=f"El usuario {usuario_data.nombre} no esta activo")

        usuario = self.sql_repository.get_usuario(usuario_data.usuario)
        if usuario is None:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        if not usuario.puede_ingresar_sistema:
            raise HTTPException(status_code=403, detail="Usuario inhabilitado")

        hash_generado = self.password_hasher.generate_hash(login_data.codigo, login_data.clave)
        if hash_generado.strip() != str(usuario.clave).strip():
            raise HTTPException(status_code=401, detail="Contrasena incorrecta")

        fecha_sistema = self._resolve_fecha_sistema()
        roles_out = self._get_roles_out(usuario_data.usuario)
        oficinas = self._get_oficinas_consulta(usuario_data.usuario)
        token = self.token_service.create_access_token(
            usuario,
            fecha_sistema,
            usuario_data.nombre_agencia or "",
        )

        return LoginResponse(
            puede_ingresar=True,
            codigo=usuario_data.usuario,
            nombre=usuario_data.nombre,
            identificacion=usuario_data.identificacion or "",
            id_agencia=usuario_data.id_agencia,
            nombre_agencia=usuario_data.nombre_agencia or "",
            activo=usuario_data.activo,
            roles=roles_out,
            oficinas_consulta=oficinas,
            token=token,
            fecha_sistema=fecha_sistema,
        )

    def _resolve_fecha_sistema(self) -> date:
        if not self.validar_fecha_sistema_en_login:
            return date.today()

        fecha_sistema = self.sql_repository.get_fecha_sistema_abierta(date.today())
        if fecha_sistema is None:
            raise HTTPException(
                status_code=403,
                detail="La fecha del sistema cambio. Ingrese nuevamente al sistema",
            )
        return fecha_sistema.fecha_sistema.date()

    def _get_roles_out(self, codigo_usuario: str) -> list[RolOut]:
        return [RolOut.model_validate(rol) for rol in self.sql_repository.get_roles_usuario(codigo_usuario)]

    def _get_enabled_user(self, codigo_usuario: str):
        usuario = self.sql_repository.get_usuario(codigo_usuario)
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if not usuario.activo or not usuario.puede_ingresar_sistema:
            raise HTTPException(status_code=403, detail="Usuario inhabilitado")
        return usuario

    def _get_oficinas_consulta(self, codigo_usuario: str) -> list[OficinaConsultaItem]:
        return [
            OficinaConsultaItem(id=row.id, nombre=row.nombre)
            for row in self.sql_repository.get_oficinas_consulta(codigo_usuario)
        ]

    def _get_menu_for_roles(self, roles: list[RolOut]) -> list[MenuChild]:
        role_codes = [rol.codigo for rol in roles]
        return self._get_menu_repository().get_menu_by_role_codes(role_codes)

    def _validate_menu_admin(self, codigo_usuario: str) -> None:
        usuario = self._get_enabled_user(codigo_usuario)
        roles_out = self._get_roles_out(usuario.usuario)
        if not any(rol.codigo == self.admin_role_code for rol in roles_out):
            raise HTTPException(status_code=403, detail="No tiene permisos para administrar el menu DataSacWeb.")

    def _validate_target_roles(self, roles_codigo: list[str]) -> list[str]:
        roles = list(dict.fromkeys(rol.strip() for rol in roles_codigo if rol.strip()))
        for codigo in roles:
            if self.sql_repository.get_rol_activo(codigo) is None:
                raise HTTPException(status_code=404, detail=f"Rol {codigo} no encontrado o inactivo.")
        return roles

    def _get_menu_repository(self) -> MongoMenuRepository:
        if self.menu_repository is None:
            self.menu_repository = MongoMenuRepository(get_mongo_datasac_app_web_menu_db_sync())
        return self.menu_repository
