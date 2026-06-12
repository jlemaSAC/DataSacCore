from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class AtsVentas(Base):
    __tablename__ = "ATS_VENTAS"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_agencia = Column('IDAGENCIA', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False)
    codigo_usuario = Column('CODIGOUSUARIO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    codigo_tipo_identificacion_cliente = Column('CODIGOTIPOIDENTIFICACIONCLIENTE', NVARCHAR(5), ForeignKey('CONTABILIDAD.ATS_TIPOIDENTIFICACION.CODIGO'), nullable=False)
    identificacion_cliente = Column('IDENTIFICACIONCLIENTE', NVARCHAR(26), nullable=False)
    codigo_tipo_comprobante = Column('CODIGOTIPOCOMPROBANTE', NVARCHAR(5), ForeignKey('CONTABILIDAD.ATS_TIPOCOMPROBANTE.CODIGO'), nullable=False)
    numero_comprobantes = Column('NUMEROCOMPROBANTES', Integer, nullable=False)
    base_imponible_0 = Column('BASEIMPONIBLE0', Numeric(18, 2), nullable=False)
    base_imponible = Column('BASEIMPONIBLE', Numeric(18, 2), nullable=False)
    base_imponible_iva = Column('BASEIMPONIBLEIVA', Numeric(18, 2), nullable=False)
    monto_iva = Column('MONTOIVA', Numeric(18, 2), nullable=False)
    valor_retencion_iva = Column('VALORRETENCIONIVA', Numeric(18, 2), nullable=False)
    valor_retencion_renta = Column('VALORRETENCIONRENTA', Numeric(18, 2), nullable=False)
    fecha_emision = Column('FECHAEMISION', DateTime, nullable=False)
    fecha_sistema = Column('FECHASISTEMA', DateTime, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    clave_acceso = Column('CLAVEACCESO', NVARCHAR(100), nullable=False)
    establecimiento = Column('ESTABLECIMIENTO', NVARCHAR(10), nullable=False)
    punto_emision = Column('PUNTOEMISION', NVARCHAR(10), nullable=False)
    secuencial = Column('SECUENCIAL', Integer, nullable=False)
