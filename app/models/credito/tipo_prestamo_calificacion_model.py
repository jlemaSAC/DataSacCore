from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.mssql import DECIMAL, NVARCHAR

from app.db.base import Base


class TipoPrestamoCalificacion(Base):
    __tablename__ = "TIPO_PRESTAMO_CALIFICACION"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_prestamo = Column('CODIGOTIPOPRESTAMO', NVARCHAR(30), ForeignKey('CREDITO.TIPO_PRESTAMO.CODIGO'), nullable=False)
    monto_inicio = Column('MONTOINICIO', DECIMAL(18, 2), nullable=False)
    monto_fin = Column('MONTOFIN', DECIMAL(18, 2), nullable=False)
    calificacion_minima = Column('CALIFICACIONMINIMA', DECIMAL(18, 2), nullable=False)
    calificacion_maxima = Column('CALIFICACIONMAXIMA', DECIMAL(18, 2), nullable=False)
    detalle = Column('DETALLE', String(150), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
