from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class FrecuenciaPago(Base):
    __tablename__ = "FRECUENCIA_PAGO"
    __table_args__ = {"schema": "CREDITO"}

    codigo = Column('CODIGO', NVARCHAR(30), primary_key=True, nullable=False)
    codigo_super = Column('CODIGOSUPER', NVARCHAR(10), nullable=True)
    id_empresa = Column('IDEMPRESA', Integer, ForeignKey('GENERAL.EMPRESA.ID'), nullable=False)
    detalle = Column('DETALLE', NVARCHAR(150), nullable=False)
    dias = Column('DIAS', Integer, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)

