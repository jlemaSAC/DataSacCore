from sqlalchemy import Column, Integer, Boolean, ForeignKey, text

from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base


class CuentaContable(Base):
    __tablename__ = "CUENTACONTABLE"
    __table_args__ = {"schema": "CONTABILIDAD"}

    codigo = Column("CODIGO", NVARCHAR(50), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(250), nullable=False)

    es_debito = Column("ESDEBITO", Boolean, nullable=False)
    id_empresa = Column("IDEMPRESA", Integer, ForeignKey("GENERAL.EMPRESA.ID"), nullable=False)
    es_de_movimiento = Column("ESDEMOVIMIENTO", Boolean, nullable=False)
    requiere_auxiliar = Column("REQUIEREAUXILIAR", Boolean, nullable=False)
    requiere_area = Column("REQUIERAAREA", Boolean, nullable=False)  # nombre según DDL
    es_bancaria = Column("ESBANCARIA", Boolean, nullable=False)
    activa = Column("ACTIVA", Boolean, nullable=False)
    requiere_documento_adicional = Column("REQUIEREDOCUMENTOADICIONAL",Boolean,nullable=False,server_default=text("0"))

    # Relaciones opcionales
    #empresa = relationship("Empresa", backref="cuentas_contables")
    # movimientos = relationship("MovimientoComprobanteContable", backref="cuenta_contable")