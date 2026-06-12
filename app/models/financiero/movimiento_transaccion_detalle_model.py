from sqlalchemy import (
    Column, Integer, String, Boolean, DECIMAL, ForeignKey
)
from sqlalchemy.orm import relationship
from app.db.base import Base


class MovimientoTransaccionDetalle(Base):
    __tablename__ = "MOVIMIENTO_TRANSACCION_DETALLE"
    __table_args__ = {"schema": "FINANCIERO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    id_movimiento_transaccion = Column("IDMOVIMIENTOTRANSACCION",Integer,ForeignKey("FINANCIERO.MOVIMIENTO_TRANSACCION.ID"),nullable=False)
    id_agencia_afectada = Column("IDAGENCIAAFECTADA",Integer,ForeignKey("GENERAL.AGENCIA.ID"),nullable=False)
    codigo_tipo_producto = Column("CODIGOTIPOPRODUCTO",String(50),ForeignKey("FINANCIERO.TIPO_PRODUCTO.CODIGO"),nullable=False)
    detalle = Column("DETALLE", String(500), nullable=True)
    id_moneda = Column("IDMONEDA",Integer,ForeignKey("GENERAL.MONEDA.ID"),nullable=False)
    debito = Column("DEBITO", Boolean, nullable=False)
    valor = Column("VALOR", DECIMAL(18, 2), nullable=False)

    # Relaciones
    movimiento_transaccion = relationship("MovimientoTransaccion", back_populates="movimiento_transaccion_detalles")
    
    movimiento_transaccion_detalles_referido = relationship("MovimientoTransaccionDetalleReferido",back_populates="movimiento_transaccion_detalles")
    
    prestamo_movimiento_transaccion_detalle = relationship("PrestamoMovimientoTransaccionDetalle",back_populates="movimiento_transaccion_detalles")
    agencia = relationship("Agencia", back_populates="movimientos_detalle")
    
    cuenta_movimiento_transaccion_detalle = relationship(
    "CuentaMovimientoTransaccionDetalle",
    back_populates="movimiento_transaccion_detalles",
    uselist=False,
    )
    
    
    # moneda = relationship("Moneda", back_populates="movimientos_detalle")
    # tipo_producto = relationship("TipoProducto", back_populates="movimientos_detalle")
    
    # movimientos_rubro = relationship("PrestamoRubroMovimientoTransaccionDetalle",back_populates="detalle_transaccion")
    