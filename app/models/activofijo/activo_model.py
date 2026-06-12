from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, LargeBinary, Numeric, text
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class Activo(Base):
    __tablename__ = "ACTIVO"
    __table_args__ = (
        Index("IX_ACTIVO_CODIGOSUPER", "CODIGOSUPER"),
        {"schema": "ACTIVOFIJO"},
    )

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_estructura = Column('IDESTRUCTURA', Integer, ForeignKey('ACTIVOFIJO.ESTRUCTURA.ID'), nullable=False)
    id_moneda = Column('IDMONEDA', Integer, ForeignKey('GENERAL.MONEDA.ID'), nullable=False)
    codigo_super = Column('CODIGOSUPER', NVARCHAR(100), nullable=True)
    detalle = Column('DETALLE', NVARCHAR(500), nullable=False)
    fecha_compra = Column('FECHACOMPRA', DateTime, nullable=False)
    valor = Column('VALOR', Numeric(18, 2), nullable=False)
    marca = Column('MARCA', NVARCHAR(100), nullable=False)
    modelo = Column('MODELO', NVARCHAR(100), nullable=False)
    serie = Column('SERIE', NVARCHAR(100), nullable=False)
    codigo_usuario = Column('CODIGOUSUARIO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    fecha = Column('FECHA', DateTime, nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)
    codigo_estado = Column('CODIGOESTADO', NVARCHAR(50), ForeignKey('ACTIVOFIJO.ESTADO_ACTIVO.CODIGO'), nullable=False)
    activa = Column('ACTIVA', Boolean, nullable=False)
    es_bien_intangible = Column('ESBIENINTANGIBLE', Boolean, nullable=False)
    fecha_inicio_calculo = Column('FECHAINICIOCALCULO', DateTime, nullable=False)
    fecha_fin_calculo = Column('FECHAFINCALCULO', DateTime, nullable=False)
    es_vehiculo = Column('ESVEHICULO', Boolean, nullable=False)
    es_bien_de_control = Column('ESBIENDECONTROL', Boolean, nullable=False)
    color = Column('COLOR', NVARCHAR(100), nullable=True)
    motor = Column('MOTOR', NVARCHAR(100), nullable=True)
    chasis = Column('CHASIS', NVARCHAR(100), nullable=True)
    placa = Column('PLACA', NVARCHAR(50), nullable=True)
    codigo_condicion = Column('CODIGOCONDICION', NVARCHAR(10), ForeignKey('ACTIVOFIJO.CONDICION_ACTIVO.CODIGO'), nullable=False)
    asegurado = Column('ASEGURADO', Boolean, nullable=False)
    codigo_homologado = Column('CODIGOHOMOLOGADO', NVARCHAR(100), nullable=True)
    id_area_ubicacion = Column('IDAREAUBICACION', Integer, ForeignKey('ACTIVOFIJO.AREA_UBICACION.ID'), nullable=False, server_default=text('1'))
    depreciacion_acumulado = Column('DEPRECIACIONACUMULADO', Numeric(18, 2), nullable=False, server_default=text('0'))
    observacion = Column('OBSERVACION', NVARCHAR(500), nullable=False, server_default=text("''"))
    codigo_qr = Column('CODIGOQR', LargeBinary, nullable=True)
    valor_anexo = Column('VALORANEXO', Numeric(18, 2), nullable=True)
    porcentaje_depreciacion = Column('PORCENTAJEDEPRECIACION', Numeric(18, 2), nullable=True)
