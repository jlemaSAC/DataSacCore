from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class ActivoFijoConstatacionFisica(Base):
    __tablename__ = "ACTIVO_FIJO_CONSTATACION_FISICA"
    __table_args__ = {"schema": "ACTIVOFIJO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_periodo = Column('IDPERIODO', Integer, ForeignKey('GENERAL.PERIODO_ANIO.ID'), nullable=False)
    id_responsable = Column('IDRESPONSABLE', Integer, ForeignKey('ACTIVOFIJO.RESPONSABLE.ID'), nullable=False)
    id_activo = Column('IDACTIVO', Integer, ForeignKey('ACTIVOFIJO.ACTIVO.ID'), nullable=False)
    codigo_usuario = Column('CODIGOUSUARIO', NVARCHAR(100), nullable=False)
    fecha_sistema = Column('FECHASISTEMA', DateTime, nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)
