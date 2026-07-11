from sqlalchemy.orm import Session

from app.models.seguridad.rol_model import Rol


class SqlRolRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_roles(self, activo: bool | None = None) -> list[Rol]:
        query = self.db.query(Rol)
        if activo is not None:
            query = query.filter(Rol.activo == activo)

        return query.order_by(Rol.nivel.asc(), Rol.nombre.asc(), Rol.codigo.asc()).all()
