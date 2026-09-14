from typing import NamedTuple

from sqlalchemy.orm import Session

from app.models.general.agencia_model import Agencia
from app.models.nomina.cargo_model import Cargo
from app.models.nomina.empleado_model import Empleado
from app.models.nomina.empleado_usuario_model import EmpleadoUsuario
from app.models.seguridad.usuario_model import Usuario


IDS_CARGOS_RECUPERACION = (79, 94, 95, 97, 104, 133)


class AsesorAgenciaData(NamedTuple):
    codigo: str
    nombre: str
    id_agencia: int
    agencia: str
    id_cargo: int
    cargo: str


class SqlAsesoresAgenciaRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def listar(self, ids_agencia: list[int]) -> list[AsesorAgenciaData]:
        rows = (
            self.db.query(
                Usuario.usuario.label("codigo"),
                Usuario.nombre.label("nombre"),
                Usuario.id_agencia.label("id_agencia"),
                Agencia.nombre.label("agencia"),
                Cargo.id.label("id_cargo"),
                Cargo.nombre.label("cargo"),
            )
            .join(Agencia, Agencia.id == Usuario.id_agencia)
            .join(EmpleadoUsuario, EmpleadoUsuario.codigo_usuario == Usuario.usuario)
            .join(Empleado, Empleado.id == EmpleadoUsuario.id_empleado)
            .join(Cargo, Cargo.id == Empleado.id_cargo)
            .filter(Usuario.id_agencia.in_(ids_agencia))
            .filter(Usuario.activo)
            .filter(Usuario.puede_ingresar_sistema)
            .filter(Agencia.activa)
            .filter(Empleado.codigo_estado_empleado == "A")
            .filter(Cargo.activo)
            .filter(Cargo.id.in_(IDS_CARGOS_RECUPERACION))
            .order_by(Agencia.nombre.asc(), Usuario.nombre.asc(), Usuario.usuario.asc())
            .distinct()
            .all()
        )
        return [
            AsesorAgenciaData(
                codigo=str(row.codigo),
                nombre=str(row.nombre),
                id_agencia=int(row.id_agencia),
                agencia=str(row.agencia),
                id_cargo=int(row.id_cargo),
                cargo=str(row.cargo),
            )
            for row in rows
        ]

