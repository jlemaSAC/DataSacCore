from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class PrestamoCancelacion(Base):
    __tablename__ = "PRESTAMOCANCELACION"
    __table_args__ = {"schema": "COLOCACION"}

    id_prestamo = Column('IDPRESTAMO', Integer, ForeignKey('COLOCACION.PRESTAMO.ID'), primary_key=True, nullable=False)
    fecha_sistema = Column('FECHASISTEMA', DateTime, nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)
    codigo_usuario = Column('CODIGOUSUARIO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    codigo_estado_anterior = Column('CODIGOESTADOANTERIOR', NVARCHAR(10), ForeignKey('COLOCACION.ESTADO_PRESTAMO.CODIGO'), nullable=True)
