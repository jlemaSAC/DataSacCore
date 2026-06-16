from datetime import date
from typing import NamedTuple

from sqlalchemy import func
from sqlalchemy.dialects.mssql import DATE
from sqlalchemy.orm import Session

from app.models.general.agencia_model import Agencia
from app.models.general.calendario_sistema_model import CalendarioSistema
from app.models.nomina.empleado_model import Empleado
from app.models.nomina.empleado_usuario_model import EmpleadoUsuario
from app.models.seguridad.rol_model import Rol
from app.models.seguridad.usuario_model import Usuario
from app.models.seguridad.usuario_oficina_consulta_model import UsuarioOficinaConsulta
from app.models.seguridad.usuario_rol_model import UsuarioRol
from app.models.sujeto.persona_model import Persona


class UsuarioLoginData(NamedTuple):
    usuario: str
    nombre: str
    identificacion: str | None
    id_agencia: int
    nombre_agencia: str | None
    activo: bool


class SqlAuthRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_usuario_login_data(self, codigo_usuario: str) -> UsuarioLoginData | None:
        row = (
            self.db.query(
                Usuario.usuario.label("usuario"),
                Usuario.nombre.label("nombre"),
                Persona.identificacion.label("identificacion"),
                Usuario.id_agencia.label("id_agencia"),
                Agencia.nombre.label("nombre_agencia"),
                Usuario.activo.label("activo"),
            )
            .outerjoin(Agencia, Agencia.id == Usuario.id_agencia)
            .outerjoin(EmpleadoUsuario, EmpleadoUsuario.codigo_usuario == Usuario.usuario)
            .outerjoin(Empleado, Empleado.id == EmpleadoUsuario.id_empleado)
            .outerjoin(Persona, Persona.id == Empleado.id_persona_natural)
            .filter(Usuario.usuario == codigo_usuario)
            .first()
        )
        if row is None:
            return None

        return UsuarioLoginData(
            usuario=row.usuario,
            nombre=row.nombre,
            identificacion=row.identificacion,
            id_agencia=row.id_agencia,
            nombre_agencia=row.nombre_agencia,
            activo=row.activo,
        )

    def get_usuario(self, codigo_usuario: str) -> Usuario | None:
        return self.db.query(Usuario).filter(Usuario.usuario == codigo_usuario).first()

    def get_roles_usuario(self, codigo_usuario: str) -> list[Rol]:
        return (
            self.db.query(Rol)
            .join(UsuarioRol, UsuarioRol.codigo_rol == Rol.codigo)
            .filter(UsuarioRol.usuario_registro == codigo_usuario)
            .filter(UsuarioRol.activo)
            .filter(Rol.activo) 
            .order_by(Rol.nivel.asc(), Rol.codigo.asc())
            .all()
        )

    def get_rol_activo(self, codigo_rol: str) -> Rol | None:
        return (
            self.db.query(Rol)
            .filter(Rol.codigo == codigo_rol)
            .filter(Rol.activo)
            .first()
        )

    def get_oficinas_consulta(self, codigo_usuario: str) -> list: # type: ignore
        return (
            self.db.query(Agencia.id, Agencia.nombre)
            .join(UsuarioOficinaConsulta, UsuarioOficinaConsulta.id_agencia == Agencia.id)
            .filter(UsuarioOficinaConsulta.codigo_usuario == codigo_usuario)
            .filter(UsuarioOficinaConsulta.activo) 
            .filter(Agencia.activa) 
            .order_by(Agencia.nombre.asc())
            .distinct()
            .all()
        )

    def get_fecha_sistema_abierta(self, fecha_referencia: date) -> CalendarioSistema | None:
        return (
            self.db.query(CalendarioSistema)
            .filter(func.cast(CalendarioSistema.fecha_sistema, DATE) == fecha_referencia)
            .filter(CalendarioSistema.se_cerro) 
            .first()
        )
