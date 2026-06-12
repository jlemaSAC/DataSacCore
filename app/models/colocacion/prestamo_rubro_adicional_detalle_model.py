# models/colocacion/prestamo_rubro_adicionaldetalle_model.py

from sqlalchemy import Column, Integer, DateTime, DECIMAL, ForeignKey, text
from sqlalchemy.dialects.mssql import NVARCHAR, ROWVERSION
from app.db.base import Base

class PrestamoRubroAdicionalDetalle(Base):
    __tablename__ = "PRESTAMO_RUBRO_ADICIONALDETALLE"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_prestamo_rubro = Column('IDPRESTAMORUBRO', Integer, ForeignKey('COLOCACION.PRESTAMO_RUBRO.ID'), nullable=False)
    codigo_usuario_ingreso = Column('CODIGOUSUARIOINGRESO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    detalle = Column('DETALLE', NVARCHAR(80), nullable=False)
    valor = Column('VALOR', DECIMAL(18, 2), nullable=False)
    fecha_sistema = Column('FECHASISTEMA', DateTime, nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)
    version = Column('VERSION', ROWVERSION, nullable=True)
    id_solicitud_rubro_manual = Column('IDSOLICITUD_RUBROMANUAL', Integer, nullable=False, default=0, server_default=text('0'))