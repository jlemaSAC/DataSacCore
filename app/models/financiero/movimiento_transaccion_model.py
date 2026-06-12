from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from app.db.base import Base

class MovimientoTransaccion(Base):
    __tablename__ = "MOVIMIENTO_TRANSACCION"
    __table_args__ = {"schema": "FINANCIERO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True)
    id_transaccion = Column('IDTRANSACCION', Integer, ForeignKey('FINANCIERO.TRANSACCION.ID'), nullable=False)
    documento = Column('DOCUMENTO', String(100), nullable=False)
    fecha_sistema = Column('FECHASISTEMA', DateTime, nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)
    codigo_usuario = Column('CODIGOUSUARIO', String(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    id_agencia_usuario = Column('IDAGENCIAUSUARIO', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False)
    se_imprimio = Column('SEIMPRIMIO', Boolean, nullable=False)
    es_reverso = Column('ESREVERSO', Boolean, nullable=False)

