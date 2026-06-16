from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.mongo import get_mongo_datasac_db_sync
from app.modules.auth.repositories.mongo_menu_repository import MongoMenuRepository
from app.modules.auth.repositories.sql_auth_repository import SqlAuthRepository
from app.modules.auth.schemas import LoginResponse, MenuChild, MenuResponse, OficinaConsultaItem, RolOut, UserLogin
from app.modules.auth.security import JwtTokenService, PasswordHasher


class AuthService:
    validar_fecha_sistema_en_login = False

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
        usuario = self.sql_repository.get_usuario(codigo_usuario)
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if not usuario.activo or not usuario.puede_ingresar_sistema:
            raise HTTPException(status_code=403, detail="Usuario inhabilitado")

        roles_out = self._get_roles_out(usuario.usuario)
        menu = self._get_menu_for_roles(roles_out)
        return MenuResponse(menu=menu)

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

    def _get_oficinas_consulta(self, codigo_usuario: str) -> list[OficinaConsultaItem]:
        return [
            OficinaConsultaItem(id=row.id, nombre=row.nombre)
            for row in self.sql_repository.get_oficinas_consulta(codigo_usuario)
        ]

    def _get_menu_for_roles(self, roles: list[RolOut]) -> list[MenuChild]:
        role_codes = [rol.codigo for rol in roles]
        if self.menu_repository is None:
            self.menu_repository = MongoMenuRepository(get_mongo_datasac_db_sync())
        return self.menu_repository.get_menu_by_role_codes(role_codes)
