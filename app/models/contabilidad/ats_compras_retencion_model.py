from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class AtsComprasRetencion(Base):
    __tablename__ = "ATS_COMPRAS_RETENCION"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_ats_compras = Column('IDATSCOMPRAS', Integer, ForeignKey('CONTABILIDAD.ATS_COMPRAS.ID'), nullable=False)
    establecimiento = Column('ESTABLECIMIENTO', NVARCHAR(10), nullable=False)
    punto_emision = Column('PUNTOEMISION', NVARCHAR(10), nullable=False)
    secuencial = Column('SECUENCIAL', NVARCHAR(20), nullable=False)
    autorizacion = Column('AUTORIZACION', NVARCHAR(80), nullable=False)
    fecha_emision = Column('FECHAEMISION', DateTime, nullable=False)
    clave_acceso = Column('CLAVEACCESO', NVARCHAR(50), nullable=False)
    impreso = Column('IMPRESO', Boolean, nullable=False)
