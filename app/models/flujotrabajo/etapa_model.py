from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class Etapa(Base):
    __tablename__ = "ETAPA"
    __table_args__ = {"schema": "FLUJOTRABAJO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(150), nullable=False)
    id_tipo_etapa = Column('IDTIPOETAPA', Integer, ForeignKey('FLUJOTRABAJO.TIPO_ETAPA.ID'), nullable=False)
    orden = Column('ORDEN', Integer, nullable=False)
    aprueba_al_menos_uno = Column('APRUEBAALMENOSUNO', Boolean, nullable=False)
    activa = Column('ACTIVA', Boolean, nullable=False)
