from sqlalchemy import Column, Integer, String, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class CuentaMovimientoTransaccionDetalle(Base):
    __tablename__ = "CUENTA_MOVIMIENTOTRANSACCIONDETALLE"
    __table_args__ = {"schema": "AHORROS"}

    id_movimiento_transaccion_detalle = Column("IDMOVIMIENTOTRANSACCIONDETALLE",Integer,ForeignKey("FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE.ID"),primary_key=True,nullable=False)
    numero_cuenta = Column("NUMEROCUENTA",String(50),ForeignKey("AHORROS.CUENTA.NUMERO"),nullable=False)
    saldo = Column("SALDO", DECIMAL(18, 2), nullable=False)
    codigo_estado_cuenta = Column("CODIGOESTADOCUENTA",String(50),ForeignKey("AHORROS.ESTADO_CUENTA.CODIGO"),nullable=False)
    
    movimiento_transaccion_detalles = relationship(
        "MovimientoTransaccionDetalle",
        back_populates="cuenta_movimiento_transaccion_detalle",  
        uselist=False,
    )
    
    cuentas = relationship("Cuenta",back_populates="cuenta_movimiento_transaccion_detalle") 
    # estado_cuenta = relationship("EstadoCuenta",back_populates="cuentas_movimiento_detalle")