from sqlalchemy.orm import Session

from app.models.nomina.cargo_model import Cargo


class SqlCargoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_cargos(self, activo: bool | None = None) -> list[Cargo]:
        query = self.db.query(Cargo)
        if activo is not None:
            query = query.filter(Cargo.activo == activo)

        return query.order_by(Cargo.nombre.asc(), Cargo.id.asc()).all()
