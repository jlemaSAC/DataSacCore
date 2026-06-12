from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoPrestamoCalificacionContableSegmento(Base):
    __tablename__ = "TIPO_PRESTAMO_CALIFICACION_CONTABLE_SEGMENTO"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_prestamo = Column('CODIGOTIPOPRESTAMO', NVARCHAR(30), ForeignKey('CREDITO.TIPO_PRESTAMO.CODIGO'), nullable=False)
    id_calificacion_contable_segmento = Column('IDCALIFICACIONCONTABLESEGMENTO', Integer, ForeignKey('CREDITO.CALIFICACION_CONTABLE_SEGMENTO.ID'), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
