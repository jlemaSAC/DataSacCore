from sqlalchemy import Column, ForeignKey, Integer

from app.db.base import Base


class MovimientoTransaccionReverso(Base):
    __tablename__ = "MOVIMIENTO_TRANSACCION_REVERSO"
    __table_args__ = {"schema": "FINANCIERO"}

    id_movimiento = Column('IDMOVIMIENTO', Integer, ForeignKey('FINANCIERO.MOVIMIENTO_TRANSACCION.ID'), primary_key=True, nullable=False)
    id_movimiento_reverso = Column('IDMOVIMIENTOREVERSO', Integer, ForeignKey('FINANCIERO.MOVIMIENTO_TRANSACCION.ID'), nullable=False)
