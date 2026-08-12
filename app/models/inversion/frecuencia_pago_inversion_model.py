from sqlalchemy import Boolean, Column, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class FrecuenciaPagoInversion(Base):
    __tablename__ = "FRECUENCIA_PAGO"
    __table_args__ = {"schema": "INVERSION"}

    codigo = Column("CODIGO", NVARCHAR(10), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(150), nullable=False)
    dias = Column("DIAS", Integer, nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
