from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class ComprobanteElectronicoSri(Base):
    __tablename__ = "COMPROBANTE_ELECTRONICO_SRI"
    __table_args__ = {"schema": "CS_CE"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    clave_acceso = Column('CLAVEACCESO', NVARCHAR(80), nullable=False)
    clave_acceso_contingencia = Column('CLAVEACCESO_CONTINGENCIA', NVARCHAR(80), nullable=False)
    autorizacion = Column('AUTORIZACION', NVARCHAR(80), nullable=False)
    fecha_autorizacion = Column('FECHA_AUTORIZACION', DateTime, nullable=False)
    fecha_creacion = Column('FECHA_CREACION', DateTime, nullable=False)
    fecha_emision = Column('FECHA_EMISION', DateTime, nullable=False)
    codigo_estado = Column('CODIGOESTADO', NVARCHAR(20), ForeignKey('CS_CAT.ESTADO_COMPROBANTE_ELECTRONICO.CODIGO'), nullable=False)
    tipo_comprobante = Column('TIPO_COMPROBANTE', NVARCHAR(10), nullable=False)
    establecimiento = Column('ESTABLECIMIENTO', NVARCHAR(5), nullable=False)
    punto_emision = Column('PUNTO_EMISION', NVARCHAR(5), nullable=False)
    secuencia = Column('SECUENCIA', NVARCHAR(10), nullable=False)
    tipo_identificacion = Column('TIPO_IDENTIFICACION', NVARCHAR(10), nullable=False)
    identificacion = Column('IDENTIFICACION', NVARCHAR(20), nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(300), nullable=False)
    email = Column('EMAIL', NVARCHAR(50), nullable=False)
    direccion = Column('DIRECCION', NVARCHAR(300), nullable=False)
    base_gravada = Column('BASEGRAVADA', Numeric(18, 2), nullable=False)
    base_iva_0 = Column('BASEIVA0', Numeric(18, 2), nullable=False)
    base_no_obj_iva = Column('BASENOOBJIVA', Numeric(18, 2), nullable=False)
    iva_0 = Column('IVA0', Numeric(18, 2), nullable=False)
    iva = Column('IVA', Numeric(18, 2), nullable=False)
    total = Column('TOTAL', Numeric(18, 2), nullable=False)
    disponible = Column('DISPONIBLE', Numeric(18, 2), nullable=False)
    usuario = Column('USUARIO', NVARCHAR(50), nullable=False)
    id_agencia = Column('IDAGENCIA', NVARCHAR(20), nullable=False)
