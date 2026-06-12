from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoPrestamoFrecuenciaPago(Base):
    __tablename__ = "TIPO_PRESTAMO_FRECUENCIA_PAGO"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_prestamo = Column('CODIGOTIPOPRESTAMO', NVARCHAR(30), ForeignKey('CREDITO.TIPO_PRESTAMO.CODIGO'), nullable=False)
    codigo_frecuencia_pago = Column('CODIGOFRECUENCIAPAGO', NVARCHAR(30), ForeignKey('CREDITO.FRECUENCIA_PAGO.CODIGO'), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
