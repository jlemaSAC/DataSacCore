from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base

class AsesorPrestamoCambio(Base):
    __tablename__ = "ASESOR_PRESTAMO_CAMBIO"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_prestamo = Column('IDPRESTAMO', Integer, ForeignKey('COLOCACION.PRESTAMO.ID'), nullable=False)
    codigo_usuario_origen = Column('CODIGOUSUARIOORIGEN', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    codigo_usuario_destino = Column('CODIGOUSUARIODESTINO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    fecha_sistema = Column('FECHASISTEMA', DateTime, nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)
    codigo_usuario = Column('CODIGOUSUARIO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
