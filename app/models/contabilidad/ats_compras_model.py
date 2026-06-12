from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class AtsCompras(Base):
    __tablename__ = "ATS_COMPRAS"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_comprobante_contable = Column('IDCOMPROBANTECONTABLE', Integer, ForeignKey('CONTABILIDAD.COMPROBANTECONTABLE.ID'), nullable=False)
    codigo_sustento = Column('CODIGOSUSTENTO', NVARCHAR(5), ForeignKey('CONTABILIDAD.ATS_CREDITOTRIBUTARIO.CODIGO'), nullable=False)
    codigo_tipo_identificacion_proveedor = Column('CODIGOTIPOIDENTIFICACIONPROVEEDOR', NVARCHAR(5), ForeignKey('CONTABILIDAD.ATS_TIPOIDENTIFICACION.CODIGO'), nullable=False)
    identificacion_proveedor = Column('IDENTIFICACIONPROVEEDOR', NVARCHAR(30), nullable=False)
    codigo_tipo_comprobante = Column('CODIGOTIPOCOMPROBANTE', NVARCHAR(5), ForeignKey('CONTABILIDAD.ATS_TIPOCOMPROBANTE.CODIGO'), nullable=False)
    fecha_registro = Column('FECHAREGISTRO', DateTime, nullable=False)
    fecha_emision = Column('FECHAEMISION', DateTime, nullable=False)
    establecimiento = Column('ESTABLECIMIENTO', NVARCHAR(6), nullable=False)
    punto_emision = Column('PUNTOEMISION', NVARCHAR(6), nullable=False)
    secuencial = Column('SECUENCIAL', NVARCHAR(9), nullable=False)
    autorizacion = Column('AUTORIZACION', NVARCHAR(80), nullable=False)
    base_imponible = Column('BASEIMPONIBLE', Numeric(18, 2), nullable=False)
    base_imponible_grabada = Column('BASEIMPONIBLEGRABADA', Numeric(18, 2), nullable=False)
    base_no_grabada_iva = Column('BASENOGRABADAIVA', Numeric(18, 2), nullable=False)
    descuento = Column('DESCUENTO', Numeric(18, 2), nullable=False)
    monto_iva = Column('MONTOIVA', Numeric(18, 2), nullable=False)
    monto_ice = Column('MONTOICE', Numeric(18, 2), nullable=False)
    valor_retencion_bienes = Column('VALORRETENCIONBIENES', Numeric(18, 2), nullable=False)
    valor_retencion_servicios = Column('VALORRETENCIONSERVICIOS', Numeric(18, 2), nullable=False)
    valor_retencion_servicios_100 = Column('VALORRETENCIONSERVICIOS100', Numeric(18, 2), nullable=False)
    monto_iva_bienes = Column('MONTOIVABIENES', Numeric(18, 2), nullable=False)
    monto_iva_servicios = Column('MONTOIVASERVICIOS', Numeric(18, 2), nullable=False)
    con_bienes = Column('CONBIENES', Boolean, nullable=False)
    con_servicios = Column('CONSERVICIOS', Boolean, nullable=False)
    con_activos_fijos = Column('CONACTIVOSFIJOS', Boolean, nullable=False)
    con_activos_diferidos = Column('CONACTIVOSDIFERIDOS', Boolean, nullable=False)
    pago_local_exterior = Column('PAGOLOCALEXTERIOR', Boolean, nullable=False)
    pais_efectivo_pago = Column('PAISEFECTIVOPAGO', NVARCHAR(3), nullable=False)
    aplica_convenio_doble_tribut = Column('APLICACONVENIODOBLETRIBUT', NVARCHAR(2), nullable=False)
    pag_ext_suj_ret_nor_leg = Column('PAGEXTSUJRETNORLEG', NVARCHAR(2), nullable=False)
    pago_regimen_fiscal = Column('PAGOREGIMENFISCAL', NVARCHAR(2), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
