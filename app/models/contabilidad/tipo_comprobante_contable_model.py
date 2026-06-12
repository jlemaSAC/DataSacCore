from sqlalchemy import Column, Boolean
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base
from sqlalchemy.orm import relationship  # opcional

class TipoComprobanteContable(Base):
    __tablename__ = "TIPO_COMPROBANTECONTABLE"
    __table_args__ = {"schema": "CONTABILIDAD"}

    codigo = Column("CODIGO", NVARCHAR(50), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(250), nullable=False)
    activa = Column("ACTIVA", Boolean, nullable=False)

    # Relación opcional (solo si la quieres)
    comprobantes = relationship("ComprobanteContable", backref="tipo_comprobante_contable")