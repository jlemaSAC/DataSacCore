from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class Proveedor(Base):
    __tablename__ = "PROVEEDOR"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_persona = Column('IDPERSONA', Integer, ForeignKey('SUJETO.PERSONA.ID'), nullable=True)
    id_agencia = Column('IDAGENCIA', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False)
    codigo_tipo_identificacion = Column('CODIGOTIPOIDENTIFICACION', NVARCHAR(5), ForeignKey('CONTABILIDAD.ATS_TIPOIDENTIFICACION.CODIGO'), nullable=False)
    identificacion = Column('IDENTIFICACION', NVARCHAR(50), nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(150), nullable=False)
    direccion = Column('DIRECCION', NVARCHAR(500), nullable=True)
    telefono = Column('TELEFONO', NVARCHAR(20), nullable=False)
    movil = Column('MOVIL', NVARCHAR(20), nullable=False)
    email = Column('EMAIL', NVARCHAR(100), nullable=False)
    contacto = Column('CONTACTO', NVARCHAR(150), nullable=False)
    es_contribuyente_especial = Column('ESCONTRIBUYENTEESPECIAL', Boolean, nullable=False)
    codigo_usuario_ingreso = Column('CODIGOUSUARIOINGRESO', NVARCHAR(100), nullable=False)
    fecha_sistema_ingreso = Column('FECHASISTEMAINGRESO', DateTime, nullable=False)
    emite_factura_electronica = Column('EMITEFACTURAELECTRONICA', Boolean, nullable=False)
    es_juridico = Column('ESJURIDICO', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    obligado_llevar_contabilidad = Column('OBLIGADOLLEVARCONTABILIDAD', Boolean, nullable=False)
    es_sociedad = Column('ESSOCIEDAD', Boolean, nullable=False)
