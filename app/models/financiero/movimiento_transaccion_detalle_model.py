from sqlalchemy import (
    Column, Integer, String, Boolean, DECIMAL, ForeignKey
)
from app.db.base import Base


class MovimientoTransaccionDetalle(Base):
    __tablename__ = "MOVIMIENTO_TRANSACCION_DETALLE"
    __table_args__ = {"schema": "FINANCIERO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True)
    id_movimiento_transaccion = Column('IDMOVIMIENTOTRANSACCION', Integer, ForeignKey('FINANCIERO.MOVIMIENTO_TRANSACCION.ID'), nullable=False)
    id_agencia_afectada = Column('IDAGENCIAAFECTADA', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False)
    codigo_tipo_producto = Column('CODIGOTIPOPRODUCTO', String(50), ForeignKey('FINANCIERO.TIPO_PRODUCTO.CODIGO'), nullable=False)
    detalle = Column('DETALLE', String(500), nullable=True)
    id_moneda = Column('IDMONEDA', Integer, ForeignKey('GENERAL.MONEDA.ID'), nullable=False)
    debito = Column('DEBITO', Boolean, nullable=False)
    valor = Column('VALOR', DECIMAL(18, 2), nullable=False)

    
    
    
    
    
    
    