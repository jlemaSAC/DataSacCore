from sqlalchemy import VARCHAR, Boolean, Column, Integer

from app.db.base import Base


class TipoAccion(Base):
    __tablename__ = "TIPOACCION"
    __table_args__ = {"schema": "LOGS"}

    id = Column('Id', Integer, primary_key=True, autoincrement=True, nullable=False)
    nombre = Column('Nombre', VARCHAR(100), nullable=False)
    descripcion = Column('Descripcion', VARCHAR(255), nullable=True)
    activo = Column('ACTIVO', Boolean, nullable=False)