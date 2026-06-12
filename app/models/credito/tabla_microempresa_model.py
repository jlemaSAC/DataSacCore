from sqlalchemy import Column, Integer

from app.db.base import Base


class TablaMicroempresa(Base):
    __tablename__ = "TABLAMICROEMPRESA"
    __table_args__ = {"schema": "CREDITO"}

    # La tabla en SQL no define PK; se usa clave compuesta logica para mapeo ORM.
    id_solicitud = Column("IDSOLICITUD", Integer, primary_key=True, nullable=False)
    meses_actividad = Column("MESESACTIVIDAD", Integer, primary_key=True, nullable=False)
