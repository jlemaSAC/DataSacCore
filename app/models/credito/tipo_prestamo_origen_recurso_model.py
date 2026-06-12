from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoPrestamoOrigenRecurso(Base):
    __tablename__ = "TIPO_PRESTAMO_ORIGEN_RECURSO"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_prestamo = Column('CODIGOTIPOPRESTAMO', NVARCHAR(30), ForeignKey('CREDITO.TIPO_PRESTAMO.CODIGO'), nullable=False)
    codigo_origen_recurso = Column('CODIGOORIGENRECURSO', NVARCHAR(30), ForeignKey('CREDITO.ORIGEN_RECURSO.CODIGO'), nullable=False)
    fecha_inicio = Column('FECHAINICIO', DateTime, nullable=False)
    fecha_fin = Column('FECHAFIN', DateTime, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
