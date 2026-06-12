from sqlalchemy import Boolean, Column
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class OrigenRecurso(Base):
    __tablename__ = "ORIGEN_RECURSO"
    __table_args__ = {"schema": "CREDITO"}

    codigo = Column('CODIGO', NVARCHAR(30), primary_key=True, nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(150), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
