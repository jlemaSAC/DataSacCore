from sqlalchemy.orm import Session

from app.models.general.agencia_model import Agencia


class SqlAgenciaCarteraRepository:
    """Resuelve el nombre de la agencia para filtrar sus snapshots Mongo."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def obtener_nombre_agencia(self, id_agencia: int) -> str | None:
        nombre = (
            self.db.query(Agencia.nombre)
            .filter(Agencia.id == id_agencia)
            .scalar()
        )
        return str(nombre).strip() if nombre else None
