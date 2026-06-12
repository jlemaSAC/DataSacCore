from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary
from sqlalchemy.dialects.mssql import DECIMAL, NVARCHAR

from app.db.base import Base


class SolicitudPrestamo(Base):
    __tablename__ = "SOLICITUD_PRESTAMO"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    numero = Column('NUMERO', Integer, nullable=False)
    renovacion = Column('RENOVACION', Boolean, nullable=True)
    cobro_rol = Column('COBROROL', Boolean, nullable=True)
    firma_conjunta = Column('FIRMACONJUNTA', Boolean, nullable=False)
    codigo_tipo_prestamo = Column('CODIGOTIPOPRESTAMO', NVARCHAR(30), ForeignKey('CREDITO.TIPO_PRESTAMO.CODIGO'), nullable=False)
    codigo_producto = Column('CODIGOPRODUCTO', NVARCHAR(50), ForeignKey('FINANCIERO.PRODUCTO.CODIGO'), nullable=False)
    id_agencia = Column('IDAGENCIA', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False)
    codigo_usuario = Column('CODIGOUSUARIO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    id_calificacion_contable_segmento = Column('IDCALIFICACIONCONTABLESEGMENTO', Integer, ForeignKey('CREDITO.CALIFICACION_CONTABLE_SEGMENTO.ID'), nullable=False)
    codigo_subcalificacion_contable = Column('CODIGOSUBCALIFICACIONCONTABLE', NVARCHAR(30), ForeignKey('CREDITO.SUBCALIFICACION_CONTABLE.CODIGO'), nullable=False)
    id_tipo_tabla_amortizacion = Column('IDTIPOTABLAAMORTIZACION', Integer, ForeignKey('CREDITO.TIPO_TABLA_AMORTIZACION.ID'), nullable=False)
    codigo_origen_recurso = Column('CODIGOORIGENRECURSO', NVARCHAR(30), ForeignKey('CREDITO.ORIGEN_RECURSO.CODIGO'), nullable=False)
    monto_solicitado = Column('MONTOSOLICITADO', DECIMAL(18, 2), nullable=False)
    monto_aprobado = Column('MONTOAPROBADO', DECIMAL(18, 2), nullable=False)
    cuotas = Column('CUOTAS', Integer, nullable=False)
    frecuencia_pago = Column('FRECUENCIAPAGO', Integer, nullable=False)
    fecha_sistema = Column('FECHASISTEMA', DateTime, nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)
    codigo_estado_solicitud = Column('CODIGOESTADOSOLICITUD', NVARCHAR(50), ForeignKey('CREDITO.ESTADO_CREDITO.CODIGO'), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    version = Column('VERSION', LargeBinary, nullable=True)
    codigo_asesor = Column('CODIGOASESOR', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    codigo_destino_credito = Column('CODIGODESTINOCREDITO', NVARCHAR(30), ForeignKey('CREDITO.DESTINOCREDITO.CODIGO'), nullable=True)

