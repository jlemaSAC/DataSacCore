from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class MovimientoTransaccionDetalleFactura(Base):
    __tablename__ = "MOVIMIENTO_TRANSACCION_DETALLE_FACTURA"
    __table_args__ = {"schema": "FINANCIERO"}

    id_movimiento_transaccion_detalle = Column(
        "IDMOVIMIENTOTRANSACCIONDETALLE",
        Integer,
        ForeignKey("FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE.ID"),
        primary_key=True,
        nullable=False,
    )
    clave_acceso = Column("CLAVEACCESO", String(100), nullable=False)

    movimiento_transaccion_detalle = relationship("MovimientoTransaccionDetalle")
