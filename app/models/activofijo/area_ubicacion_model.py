from sqlalchemy import Boolean, Column, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class AreaUbicacion(Base):
    __tablename__ = "AREA_UBICACION"
    __table_args__ = {"schema": "ACTIVOFIJO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(100), nullable=False)
    codigo = Column("CODIGO", NVARCHAR(3), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
