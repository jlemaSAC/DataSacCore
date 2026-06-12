from sqlalchemy import Column, Integer, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base


class MovimientoComprobanteContableTransaccion(Base):
    __tablename__ = "MOVIMIENTOCOMPROBANTECONTABLE_TRANSACCION"
    __table_args__ = (
        Index(
            "IX_MOVIMIENTOCOMPROBANTECONTABLE_TRANSACCION",
            "IDMOVIMIENTOTRANSACCIONDETALLE", "ESTRANSACCION"
        ),
        Index(
            "IX_MOVIMIENTOCOMPROBANTECONTABLE_TRANSACCION_IDMOVIMIENTOCONTABLE",
            "IDMOVIMIENTOCONTABLE"
        ),
        {"schema": "CONTABILIDAD"},
    )

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_movimiento_contable = Column("IDMOVIMIENTOCONTABLE",Integer,ForeignKey("CONTABILIDAD.MOVIMIENTOCOMPROBANTECONTABLE.ID"),nullable=False,)
    id_movimiento_transaccion_detalle = Column(
    "IDMOVIMIENTOTRANSACCIONDETALLE", Integer, nullable=False)
    es_transaccion = Column("ESTRANSACCION", Boolean, nullable=False)
    # Relación opcional hacia el movimiento contable
    movimiento_comprobante_contable = relationship("MovimientoComprobanteContable", backref="transacciones")