from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class CalificacionContableSegmento(Base):
    __tablename__ = "CALIFICACION_CONTABLE_SEGMENTO"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_calificacion_contable = Column('CODIGOCALIFICACIONCONTABLE', NVARCHAR(30), ForeignKey('CREDITO.CALIFICACION_CONTABLE.CODIGO'), nullable=False)
    codigo_destino_financiero = Column('CODIGODESTINO_FINANCIERO', NVARCHAR(30), ForeignKey('CREDITO.DESTINO_FINANCIERO.CODIGO'), nullable=False)
    id_empresa = Column('IDEMPRESA', Integer, ForeignKey('GENERAL.EMPRESA.ID'), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
