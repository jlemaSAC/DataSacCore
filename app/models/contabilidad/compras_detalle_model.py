from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, Numeric, text
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class ComprasDetalle(Base):
    __tablename__ = "COMPRAS_DETALLE"
    __table_args__ = (
        Index("IX_COMPRAS_DETALLE_IDCOMPRAS", "IDCOMPRAS"),
        {"schema": "CONTABILIDAD"},
    )

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_compras = Column('IDCOMPRAS', Integer, ForeignKey('CONTABILIDAD.COMPRAS.ID'), nullable=False)
    codigo_cuenta_contable = Column('CODIGOCUENTACONTABLE', NVARCHAR(50), ForeignKey('CONTABILIDAD.CUENTACONTABLE.CODIGO'), nullable=False)
    detalle = Column('DETALLE', NVARCHAR(350), nullable=False)
    cantidad = Column('CANTIDAD', Integer, nullable=False)
    valor_unitario = Column('VALORUNITARIO', Numeric(18, 6), nullable=False)
    descuento = Column('DESCUENTO', Numeric(18, 2), nullable=False)
    es_bien = Column('ESBIEN', Boolean, nullable=False)
    es_activo_fijo = Column('ESACTIVOFIJO', Boolean, nullable=False)
    no_objeto_iva = Column('NO_OBJETOIVA', Boolean, nullable=False)
    iva_0 = Column('IVA0', Boolean, nullable=False)
    iva_12 = Column('IVA12', Boolean, nullable=False)
    iva_14 = Column('IVA14', Boolean, nullable=False)
    subtotal = Column('SUBTOTAL', Numeric(18, 2), nullable=False)
    impuesto = Column('IMPUESTO', Numeric(18, 3), nullable=False)
    monto_ice = Column('MONTOICE', Numeric(18, 2), nullable=False)
    total = Column('TOTAL', Numeric(18, 2), nullable=False)
    es_proveeduria = Column('ESPROVEEDURIA', Boolean, nullable=True)
    id_tarifa_sri_iva = Column('IDTARIFASRIIVA', Integer, nullable=False, server_default=text('0'))
