from sqlalchemy import Column, Boolean
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base

class EstadoPrestamoRubro(Base):
    __tablename__ = "ESTADO_PRESTAMORUBRO"
    __table_args__ = {"schema": "COLOCACION"}

    codigo = Column('CODIGO', NVARCHAR(10), primary_key=True, nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(150), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
