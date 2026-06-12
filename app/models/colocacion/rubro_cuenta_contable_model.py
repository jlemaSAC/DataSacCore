from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class RubroCuentaContable(Base):
    __tablename__ = "RUBRO_CUENTACONTABLE"
    __table_args__ = {"schema": "COLOCACION"}

    id_rubro = Column("IDRUBRO", Integer, ForeignKey("COLOCACION.RUBRO.ID"), primary_key=True, nullable=False)
    codigo_cuenta_contable = Column("CODIGOCUENTACONTABLE", String(50), ForeignKey("CONTABILIDAD.CUENTACONTABLE.CODIGO"), nullable=False)

    rubros = relationship("Rubro", back_populates="rubro_cuenta_contable")
    