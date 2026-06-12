from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base


class MovimientoTransaccionDetalleReferido(Base):
    __tablename__ = "MOVIMIENTO_TRANSACCIONDETALLE_REFERIDO"
    __table_args__ = {"schema": "FINANCIERO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_movimiento_transaccion_detalle = Column('IDMOVIMIENTOTRANSACCIONDETALLE', Integer, ForeignKey('FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE.ID'), nullable=False)
    codigo_usuario_referido = Column('CODIGOUSUARIOREFERIDO', String(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    
