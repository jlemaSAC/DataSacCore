from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR, DECIMAL
from sqlalchemy.orm import relationship
from app.db.base import Base


class PrestamoMovimientoTransaccionDetalle(Base):
    __tablename__ = "PRESTAMO_MOVIMIENTOTRANSACCIONDETALLE"
    __table_args__ = ({"schema": "COLOCACION"})

    id_movimiento_transaccion_detalle = Column("IDMOVIMIENTOTRANSACCIONDETALLE",Integer,ForeignKey("FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE.ID"),primary_key=True,nullable=False)
    id_prestamo = Column("IDPRESTAMO",Integer,ForeignKey("COLOCACION.PRESTAMO.ID"),nullable=False)
    saldo = Column("SALDO", DECIMAL(18, 2), nullable=False)
    codigo_estado = Column("CODIGOESTADO",NVARCHAR(10),ForeignKey("COLOCACION.ESTADO_PRESTAMO.CODIGO"),nullable=False)
    
    prestamos = relationship("Prestamo", back_populates="prestamo_movimiento_transaccion_detalle")
    estado_prestamo = relationship("EstadoPrestamo", back_populates="prestamo_movimiento_transaccion_detalle")
    movimiento_transaccion_detalles = relationship("MovimientoTransaccionDetalle",back_populates="prestamo_movimiento_transaccion_detalle")

