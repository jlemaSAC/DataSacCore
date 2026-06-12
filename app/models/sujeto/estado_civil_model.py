from sqlalchemy import Boolean, Column
from sqlalchemy.dialects.mssql import NCHAR, NVARCHAR

from app.db.base import Base


class EstadoCivil(Base):
    __tablename__ = "ESTADO_CIVIL"
    __table_args__ = {"schema": "SUJETO"}

    codigo = Column('CODIGO', NVARCHAR(10), primary_key=True, nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(50), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    codigo_uafe = Column('CODIGOUAFE', NCHAR(1), nullable=True)

