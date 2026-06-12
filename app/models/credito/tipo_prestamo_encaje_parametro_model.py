from sqlalchemy import Boolean, Column, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoPrestamoEncajeParametro(Base):
    __tablename__ = "TIPO_PRESTAMO_ENCAJE_PARAMETRO"
    __table_args__ = {"schema": "CREDITO"}

    codigo_tipo_prestamo = Column('CODIGOTIPOPRESTAMO', NVARCHAR(30), ForeignKey('CREDITO.TIPO_PRESTAMO.CODIGO'), primary_key=True, nullable=False)
    es_automatico = Column('ESAUTOMATICO', Boolean, nullable=False)
    es_financiado = Column('ESFINANCIADO', Boolean, nullable=False)
