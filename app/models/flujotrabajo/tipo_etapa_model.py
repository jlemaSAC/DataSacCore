from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoEtapa(Base):
    __tablename__ = "TIPO_ETAPA"
    __table_args__ = {"schema": "FLUJOTRABAJO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(150), nullable=False)
    id_empresa = Column('IDEMPRESA', Integer, ForeignKey('GENERAL.EMPRESA.ID'), nullable=False)
    activa = Column('ACTIVA', Boolean, nullable=False)
    es_comprobante = Column('ESCOMPROBANTE', Boolean, nullable=False)
    es_solicitud = Column('ESSOLICITUD', Boolean, nullable=False)
    es_solicitud_administrativa = Column('ESSOLICITUDADMINISTRATIVA', Boolean, nullable=False)
