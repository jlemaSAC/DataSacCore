from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, Index, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base


class MovimientoComprobanteContable(Base):
    __tablename__ = "MOVIMIENTOCOMPROBANTECONTABLE"
    __table_args__ = (
        Index(
            "IX_MOVIMIENTOCOMPROBANTECONTABLE_CODIGOCUENTA_IDAGENCIA_FECHACOMPROBANTE",
            "CODIGOCUENTA", "IDAGENCIA", "FECHACOMPROBANTE"
        ),
        Index(
            "IX_MOVIMIENTOCOMPROBANTECONTABLE_ESDEBITO",
            "ESDEBITO",
            mssql_include=["IDCOMPROBANTE", "VALOR"]
        ),
        Index(
            "IX_MOVIMIENTOCOMPROBANTECONTABLE_IDCOMPROBANTE_ESDEBITO",
            "IDCOMPROBANTE", "ESDEBITO"
        ),
        {"schema": "CONTABILIDAD"},
    )

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_comprobante = Column('IDCOMPROBANTE', Integer, ForeignKey('CONTABILIDAD.COMPROBANTECONTABLE.ID'), nullable=False)
    es_debito = Column('ESDEBITO', Boolean, nullable=False)
    fecha_comprobante = Column('FECHACOMPROBANTE', DateTime, nullable=False)
    codigo_cuenta = Column('CODIGOCUENTA', NVARCHAR(50), ForeignKey('CONTABILIDAD.CUENTACONTABLE.CODIGO'), nullable=False)
    id_agencia = Column('IDAGENCIA', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False)
    orden = Column('ORDEN', Integer, nullable=False)
    detalle = Column('DETALLE', NVARCHAR(500), nullable=False)
    valor = Column('VALOR', Numeric(18, 2), nullable=False)

    # Relaciones (opcionales, útiles para navegación)
    
