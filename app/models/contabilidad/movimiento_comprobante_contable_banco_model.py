from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base


class MovimientoComprobanteContableBanco(Base):
    __tablename__ = "MOVIMIENTOCOMPROBANTECONTABLE_BANCO"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id_movimiento_contable = Column("IDMOVIMIENTOCONTABLE",Integer,ForeignKey("CONTABILIDAD.MOVIMIENTOCOMPROBANTECONTABLE.ID"),primary_key=True,nullable=False,)
    documento_banco = Column("DOCUMENTOBANCO", NVARCHAR(250), nullable=False)
    se_concilio = Column("SECONCILIO", Boolean, nullable=False)

    
    movimiento_comprobante_contable = relationship("MovimientoComprobanteContable",back_populates="movimiento_comprobante_contable_banco",uselist=False,)