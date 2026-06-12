from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class AtsRetencionRenta(Base):
    __tablename__ = "ATS_RETENCION_RENTA"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column('IDEMPRESA', Integer, ForeignKey('GENERAL.EMPRESA.ID'), nullable=False)
    codigo_cuenta_contable = Column('CODIGOCUENTACONTABLE', NVARCHAR(50), ForeignKey('CONTABILIDAD.CUENTACONTABLE.CODIGO'), nullable=False)
    codigo = Column('CODIGO', NVARCHAR(10), nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(500), nullable=False)
    porcentaje = Column('PORCENTAJE', Numeric(18, 2), nullable=False)
    formulario = Column('FORMULARIO', Integer, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
