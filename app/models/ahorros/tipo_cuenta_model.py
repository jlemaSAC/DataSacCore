from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR, NCHAR, DECIMAL
from app.db.base import Base


class TipoCuenta(Base):
    __tablename__ = "TIPO_CUENTA"
    __table_args__ = {"schema": "AHORROS"}

    codigo = Column('CODIGO', NVARCHAR(50, collation='Modern_Spanish_CI_AS'), primary_key=True, nullable=False)
    id_empresa = Column('IDEMPRESA', Integer, ForeignKey('GENERAL.EMPRESA.ID'), nullable=False)
    codigo_producto = Column('CODIGOPRODUCTO', NVARCHAR(50, collation='Modern_Spanish_CI_AS'), ForeignKey('FINANCIERO.PRODUCTO.CODIGO'), nullable=False)
    siglas = Column('SIGLAS', NVARCHAR(10, collation='Modern_Spanish_CI_AS'), nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(150, collation='Modern_Spanish_CI_AS'), nullable=False)
    saldo_minimo = Column('SALDOMINIMO', DECIMAL(18, 2), nullable=False)
    valor_minimo_apertura = Column('VALORMINIMOAPERTURA', DECIMAL(18, 2), nullable=False)
    determina_socio = Column('DETERMINASOCIO', Boolean, nullable=False)
    multicuenta = Column('MULTICUENTA', Boolean, nullable=False)
    provisiona_interes = Column('PROVISIONAINTERES', Boolean, nullable=False)
    permite_encaje = Column('PERMITEENCAJE', Boolean, nullable=False)
    debito_prestamo = Column('DEBITOPRESTAMO', Boolean, nullable=False)
    periodo_capitalizacion = Column('PERIODOCAPITALIZACION', NVARCHAR(50, collation='Modern_Spanish_CI_AS'), nullable=False)
    es_certificado_aportacion = Column('ESCERTIFICADOAPORTACION', Boolean, nullable=False)
    es_programado = Column('ESPROGRAMADO', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    codigo_tipo_riesgo_sarf = Column('CODIGOTIPORIESGOSARF', NCHAR(1, collation='Modern_Spanish_CI_AS'), ForeignKey('SAC_UAFE.TIPO_RIESGOSARF.CODIGO'), nullable=False)
    codigo_tipo_producto_sarf = Column('CODIGOTIPOPRODUCTOSARF', NCHAR(3, collation='Modern_Spanish_CI_AS'), ForeignKey('SAC_UAFE.TIPO_PRODUCTOSARF.CODIGO'), nullable=False)
    permite_transferencia = Column('PERMITETRANSFERENCIA', Boolean, nullable=False)
    permite_tarjeta_debito = Column('PERMITETARJETADEBITO', Boolean, nullable=False)
    orden_recibe_transferencia = Column('ORDENRECIBETRANSFERENCIA', Integer, nullable=False)