from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.db.base import Base


class Transaccion(Base):
    __tablename__ = "TRANSACCION"
    __table_args__ = {"schema": "FINANCIERO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column('IDEMPRESA', Integer, ForeignKey('GENERAL.EMPRESA.ID'), nullable=False)

    codigo_tipo_producto = Column('CODIGOTIPOPRODUCTO', String(50), ForeignKey('FINANCIERO.TIPO_PRODUCTO.CODIGO'), nullable=False)
    codigo_tipo_producto_forma_pago = Column('CODIGOTIPOPRODUCTOFORMAPAGO', String(50), ForeignKey('FINANCIERO.TIPO_PRODUCTO.CODIGO'), nullable=False)
    codigo_tipo_canal_sbs = Column('CODIGOTIPOCANALSBS', String(10), ForeignKey('FINANCIERO.TIPO_CANAL_SBS.CODIGO'), nullable=False)
    id_generador_contable = Column('IDGENERADORCONTABLE', Integer, ForeignKey('CONTABILIDAD.GENERADOR_CONTABLE.ID'), nullable=False)

    codigo = Column('CODIGO', String(50), nullable=False)
    siglas = Column('SIGLAS', String(10), nullable=False)
    nombre = Column('NOMBRE', String(150), nullable=False)

    debito = Column('DEBITO', Boolean, nullable=False)
    operativo = Column('OPERATIVO', Boolean, nullable=False)
    se_visualiza = Column('SEVISUALIZA', Boolean, nullable=False)
    usuario_define_origen = Column('USUARIODEFINEORIGEN', Boolean, nullable=False)
    utiliza_papeleta = Column('UTILIZAPAPELETA', Boolean, nullable=False)
    valida_firmas = Column('VALIDAFIRMAS', Boolean, nullable=False)
    con_numero_producto = Column('CONNUMEROPRODUCTO', Boolean, nullable=False)
    anexo2 = Column('ANEXO2', Boolean, nullable=False)
    permite_reverso = Column('PERMITEREVERSO', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    permite_terceras_personas = Column('PERMITETERCERASPERSONAS', Boolean, nullable=False)
    revisa_especies_falsificadas = Column('REVISAESPECIESFALSIFICADAS', Boolean, nullable=False)
    permite_ingresar_motivo = Column('PERMITEINGRESARMOTIVO', Boolean, nullable=False)
    codigo_tipo_transaccion = Column('CODIGOTIPOTRANSACCION', String(2), nullable=False)
    permite_conexion_contadora = Column('PERMITECONEXIONCONTADORA', Boolean, nullable=False, default=False)
    permite_rifa = Column('PERMITERIFA', Boolean, nullable=False, default=False)

    # ----------------------
    # ----------------------

    # Dos FKs hacia TIPO_PRODUCTO: especifica foreign_keys en ambos lados

