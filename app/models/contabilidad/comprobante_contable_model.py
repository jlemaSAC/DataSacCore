from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, Index, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base


class ComprobanteContable(Base):
    __tablename__ = "COMPROBANTECONTABLE"
    __table_args__ = (
        Index("IX_COMPROBANTECONTABLE", "FECHA", "CODIGOTIPOCOMPROBANTE", "CODIGOESTADO"),
        Index("IX_COMPROBANTECONTABLE_1", "FECHA", "CODIGOESTADO"),
        {"schema": "CONTABILIDAD"},
    )

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    documento = Column('DOCUMENTO', Integer, nullable=False)
    codigo_tipo_comprobante = Column('CODIGOTIPOCOMPROBANTE', NVARCHAR(50), ForeignKey('CONTABILIDAD.TIPO_COMPROBANTECONTABLE.CODIGO'), nullable=False)
    fecha = Column('FECHA', DateTime, nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)
    id_agencia = Column('IDAGENCIA', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False)
    id_agencia_contabiliza = Column('IDAGENCIACONTABILIZA', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False)
    concepto = Column('CONCEPTO', NVARCHAR(1200), nullable=False)
    codigo_usuario = Column('CODIGOUSUARIO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    id_moneda = Column('IDMONEDA', Integer, ForeignKey('GENERAL.MONEDA.ID'), nullable=False)
    impreso = Column('IMPRESO', Boolean, nullable=False)
    codigo_estado = Column('CODIGOESTADO', NVARCHAR(50), ForeignKey('CONTABILIDAD.ESTADO_COMPROBANTECONTABLE.CODIGO'), nullable=False)
    cotizacion = Column('COTIZACION', Numeric(18, 2), nullable=False)

    # Relaciones (opcionales)
