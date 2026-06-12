from sqlalchemy import Column, Integer, NVARCHAR, DateTime, ForeignKey
from app.db.base import Base

class PrestamoJudicial(Base):
    __tablename__ = "PRESTAMO_JUDICIAL"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_prestamo = Column('IDPRESTAMO', Integer, ForeignKey('COLOCACION.PRESTAMO.ID'), nullable=False)
    id_abogado = Column('IDABOGADO', Integer, ForeignKey('COBRANZA.ABOGADO.ID'), nullable=False)
    numero_juicio = Column('NUMEROJUICIO', NVARCHAR(50), nullable=False)
    comentario = Column('COMENTARIO', NVARCHAR(250), nullable=False)
    codigo_usuario = Column('CODIGOUSUARIO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    fecha = Column('FECHA', DateTime, nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)