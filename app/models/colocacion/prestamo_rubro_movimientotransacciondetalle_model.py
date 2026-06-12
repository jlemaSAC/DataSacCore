from sqlalchemy import (
    Column, Integer, DECIMAL, String, ForeignKey
)
from app.db.base import Base

class PrestamoRubroMovimientoTransaccionDetalle(Base):
    __tablename__ = "PRESTAMO_RUBRO_MOVIMIENTOTRANSACCIONDETALLE"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True)
    id_movimiento_transaccion_detalle = Column('IDMOVIMIENTOTRANSACCIONDETALLE', Integer, ForeignKey('FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE.ID'), nullable=False)
    id_prestamo = Column('IDPRESTAMO', Integer, ForeignKey('COLOCACION.PRESTAMO.ID'), nullable=False)
    id_rubro = Column('IDRUBRO', Integer, ForeignKey('COLOCACION.RUBRO.ID'), nullable=False)
    id_forma_pago = Column('IDFORMAPAGO', Integer, ForeignKey('FINANCIERO.FORMA_PAGO.ID'), nullable=False)
    cuota = Column('CUOTA', Integer, nullable=False)
    valor = Column('VALOR', DECIMAL(18, 2), nullable=False)
    saldo = Column('SALDO', DECIMAL(18, 2), nullable=False)
    codigo_estado = Column('CODIGOESTADO', String(10), ForeignKey('COLOCACION.ESTADO_PRESTAMORUBRO.CODIGO'), nullable=False)
