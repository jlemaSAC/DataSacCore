from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class Deposito(Base):
    __tablename__ = "DEPOSITO"
    __table_args__ = {"schema": "INVERSION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column("IDEMPRESA", Integer, ForeignKey("GENERAL.EMPRESA.ID"), nullable=True)
    codigo = Column("CODIGO", NVARCHAR(40), nullable=False)
    codigo_tipo_deposito = Column(
        "CODIGOTIPODEPOSITO",
        NVARCHAR(20),
        ForeignKey("INVERSION.TIPO_DEPOSITO.CODIGO"),
        nullable=False,
    )
    codigo_producto = Column(
        "CODIGOPRODUCTO",
        NVARCHAR(50),
        ForeignKey("FINANCIERO.PRODUCTO.CODIGO"),
        nullable=False,
    )
    monto = Column("MONTO", Numeric(18, 2), nullable=False)
    tasa = Column("TASA", Numeric(18, 2), nullable=False)
    variacion_tasa = Column("VARIACION_TASA", Numeric(18, 2), nullable=False)
    plazo = Column("PLAZO", Integer, nullable=False)
    pago_periodico_interes = Column("PAGOPERIODICOINTERES", Boolean, nullable=False)
    fecha_creacion = Column("FECHACREACION", DateTime, nullable=False)
    fecha_vencimiento = Column("FECHAVENCIMIENTO", DateTime, nullable=False)
    codigo_estado_deposito = Column(
        "CODIGOESTADODEPOSITO",
        NVARCHAR(10),
        ForeignKey("INVERSION.ESTADO_DEPOSITO.CODIGO"),
        nullable=False,
    )
    id_moneda = Column("IDMONEDA", Integer, ForeignKey("GENERAL.MONEDA.ID"), nullable=False)
    id_agencia = Column("IDAGENCIA", Integer, ForeignKey("GENERAL.AGENCIA.ID"), nullable=False)
    codigo_usuario = Column(
        "CODIGOUSUARIO",
        NVARCHAR(100),
        ForeignKey("SEGURIDAD.USUARIO.USUARIO"),
        nullable=False,
    )
    fecha_proceso = Column("FECHAPROCESO", DateTime, nullable=False)
    fecha_fin_dia = Column("FECHAFINDIA", DateTime, nullable=True)
    version = Column("VERSION", LargeBinary, nullable=True)
    codigo_tipo_firma = Column(
        "CODIGOTIPOFIRMA",
        NVARCHAR(50),
        ForeignKey("INVERSION.TIPO_FIRMADPF.CODIGO"),
        nullable=False,
    )
    es_persona_natural = Column("ESPERSONANATURAL", Boolean, nullable=False)
    pertenece_bolsa = Column("PERTENECEBOLSA", Boolean, nullable=False)
