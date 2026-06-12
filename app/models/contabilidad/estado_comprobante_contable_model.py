from sqlalchemy import Column, Integer, Boolean, ForeignKey

from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base


class EstadoComprobanteContable(Base):
    __tablename__ = "ESTADO_COMPROBANTECONTABLE"
    __table_args__ = {"schema": "CONTABILIDAD"}

    codigo = Column("CODIGO", NVARCHAR(50), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(150), nullable=False)
    id_empresa = Column("IDEMPRESA", Integer, ForeignKey("GENERAL.EMPRESA.ID"), nullable=False)
    activa = Column("ACTIVA", Boolean, nullable=False)

    # Relación opcional
    #empresa = relationship("Empresa", backref="estados_comprobantes")
    # Si quieres navegar desde ComprobanteContable, puedes agregar allí:
    # estado = relationship("EstadoComprobanteContable", backref="comprobantes")