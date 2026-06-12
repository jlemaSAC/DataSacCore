from sqlalchemy import Column, Integer, Boolean, ForeignKey, text
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base


class MovimientoComprobanteContableDocumentoAdicional(Base):
    __tablename__ = "MOVIMIENTOCOMPROBANTECONTABLE_DOCUMENTOADICIONAL"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id_movimiento_contable = Column('IDMOVIMIENTOCONTABLE', Integer, ForeignKey('CONTABILIDAD.MOVIMIENTOCOMPROBANTECONTABLE.ID'), primary_key=True, nullable=False)
    documento = Column('DOCUMENTO', NVARCHAR(250), nullable=False)
    conciliado = Column('CONCILIADO', Boolean, nullable=False, server_default=text('1'))
    
    
