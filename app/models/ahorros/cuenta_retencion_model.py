from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class CuentaRetencion(Base):
    __tablename__ = "CUENTA_RETENCION"
    __table_args__ = {"schema": "AHORROS"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    numero_cuenta = Column('NUMEROCUENTA', NVARCHAR(50), ForeignKey('AHORROS.CUENTA.NUMERO'), nullable=False)
    fecha_emision = Column('FECHAEMISION', DateTime, nullable=False)
    base_imponible = Column('BASEIMPONIBLE', Numeric(18, 2), nullable=False)
    valor_rendimiento = Column('VALORRENDIMIENTO', Numeric(18, 2), nullable=False)
    porcentaje_rendimiento = Column('PORCENTAJERENDIMIENTO', Numeric(18, 2), nullable=False)
    valor_retencion = Column('VALORRETENCION', Numeric(18, 2), nullable=False)
    codigo_retencion = Column('CODIGORETENCION', NVARCHAR(50), nullable=False)
    establecimiento = Column('ESTABLECIMIENTO', String(5), nullable=False)
    punto_emision = Column('PUNTOEMISION', String(5), nullable=False)
    secuencial_comprobante = Column('SECUENCIALCOMPROBANTE', String(10), nullable=False)
    autorizacion = Column('AUTORIZACION', String(70), nullable=False)
    pago_local_exterior = Column('PAGOLOCALEXTERIOR', Boolean, nullable=False)
    pais_efectivo_pago = Column('PAISEFECTIVOPAGO', NVARCHAR(3), nullable=False)
    aplica_convenio_doble_tribut = Column('APLICACONVENIODOBLETRIBUT', NVARCHAR(2), nullable=False)
    pag_ext_suj_ret_nor_leg = Column('PAGEXTSUJRETNORLEG', NVARCHAR(2), nullable=False)
    pago_regimen_fiscal = Column('PAGOREGIMENFISCAL', NVARCHAR(2), nullable=False)
    esta_impreso = Column('ESTAIMPRESO', Boolean, nullable=False)
    esta_anulado = Column('ESTAANULADO', Boolean, nullable=False)
    clave_acceso = Column('CLAVEACCESO', String(50), nullable=False)
