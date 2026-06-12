from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TransferenciaInstitucion(Base):
    __tablename__ = "TRANSFERENCIA_INSTITUCION"
    __table_args__ = {"schema": "AHORROS"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(150), nullable=False)
    codigo_tipo_institucion_transferencia = Column('CODIGOTIPOINSTITUCIONTRANSFERENCIA', NVARCHAR(10), ForeignKey('AHORROS.TIPO_INSTITUCION_TRANSFERENCIA.CODIGO'), nullable=False)
    cuenta_bce = Column('CUENTABCE', NVARCHAR(20), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
