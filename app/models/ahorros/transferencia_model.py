from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, text
from sqlalchemy.dialects.mssql import DECIMAL, NVARCHAR

from app.db.base import Base


class Transferencia(Base):
    __tablename__ = "TRANSFERENCIA"
    __table_args__ = {"schema": "AHORROS"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_transferencia_institucion = Column('IDTRANSFERENCIAINSTITUCION', Integer, ForeignKey('AHORROS.TRANSFERENCIA_INSTITUCION.ID'), nullable=False)
    codigo_estado = Column('CODIGOESTADO', NVARCHAR(10), nullable=False)
    codigo_tipo_identificacion = Column('CODIGOTIPOIDENTIFICACION', NVARCHAR(20), nullable=False)
    identificacion = Column('IDENTIFICACION', NVARCHAR(20), nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(250), nullable=False)
    codigo_tipo_cuenta = Column('CODIGOTIPOCUENTA', NVARCHAR(10), ForeignKey('AHORROS.TIPO_CUENTA_TRANSFERENCIA.CODIGO'), nullable=False)
    cuenta = Column('CUENTA', NVARCHAR(50), nullable=False)
    codigo_concepto = Column('CODIGOCONCEPTO', NVARCHAR(10), ForeignKey('AHORROS.CONCEPTO_TRANSFERENCIA.CODIGO'), nullable=False)
    detalle = Column('DETALLE', NVARCHAR(250), nullable=False)
    valor = Column('VALOR', DECIMAL(18, 2), nullable=False)
    es_web = Column('ESWEB', Boolean, nullable=False)
    id_agencia = Column('IDAGENCIA', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False)
    codigo_usuario = Column('CODIGOUSUARIO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    fecha_sistema = Column('FECHASISTEMA', DateTime, nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)
    email = Column('EMAIL', NVARCHAR(100), nullable=True)
    es_banred = Column('ESBANRED', Boolean, server_default=text('0'), nullable=True)
