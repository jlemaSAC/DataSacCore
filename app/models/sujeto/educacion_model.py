from sqlalchemy import Boolean, Column
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class Educacion(Base):
    __tablename__ = "EDUCACION"
    __table_args__ = {"schema": "SUJETO"}

    codigo = Column('CODIGO', NVARCHAR(10), primary_key=True, nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(50), nullable=False)
    profesion_obligatoria = Column('PROFESIONOBLIGATORIA', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)

