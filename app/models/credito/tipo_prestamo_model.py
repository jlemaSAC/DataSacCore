from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR, NCHAR, DECIMAL
from sqlalchemy.orm import relationship
from app.db.base import Base


class TipoPrestamo(Base):
    __tablename__ = "TIPO_PRESTAMO"
    __table_args__ = {"schema": "CREDITO"}

    codigo = Column("CODIGO", NVARCHAR(30), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(150), nullable=False)
    siglas = Column("SIGLAS", NVARCHAR(10), nullable=False)
    id_empresa = Column("IDEMPRESA", Integer, ForeignKey("GENERAL.EMPRESA.ID"), nullable=False)
    monto_minimo = Column("MONTOMINIMO", DECIMAL(18, 2), nullable=False)
    monto_maximo = Column("MONTOMAXIMO", DECIMAL(18, 2), nullable=False)
    plazo_minimo_dias = Column("PLAZOMINIMODIAS", Integer, nullable=False)
    plazo_maximo_dias = Column("PLAZOMAXIMODIAS", Integer, nullable=False)
    calificacion_minima = Column("CALIFICACIONMINIMA", Integer, nullable=False)
    dias_reajuste_minimo = Column("DIASREAJUSTEMINIMO", Integer, nullable=False)
    numero_maximo_garantias_vigentes = Column("NUMEROMAXIMOGARANTIASVIGENTES", Integer, nullable=False)
    pago_cuota_completa = Column("PAGOCUOTACOMPLETA", Boolean, nullable=False)
    operativo = Column("OPERATIVO", Boolean, nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
    es_linea_credito = Column("ESLINEACREDITO", Boolean, nullable=False)
    es_agricola = Column("ESAGRICOLA", Boolean, nullable=False)
    es_grupal = Column("ESGRUPAL", Boolean, nullable=False)
    numero_max_cuotas_gracia = Column("NUMEROMAXCUOTASGRACIA", Integer, nullable=False)
    orden = Column("ORDEN", Integer, nullable=False)
    con_encaje = Column("CONENCAJE", Boolean, nullable=False)
    es_confirma_conyuge = Column("ESCONFIRMACONYUGE", Boolean, nullable=False)
    codigo_tipo_riesgo_sarf = Column("CODIGOTIPORIESGOSARF",NCHAR(1),ForeignKey("SAC_UAFE.TIPO_RIESGOSARF.CODIGO"),nullable=False,)
    codigo_tipo_producto_sarf = Column("CODIGOTIPOPRODUCTOSARF",NCHAR(3),ForeignKey("SAC_UAFE.TIPO_PRODUCTOSARF.CODIGO"),nullable=False,)
    controla_certificado_deposito = Column("CONTROLACERTIFICADODEPOSITO", Boolean, nullable=False)
    controla_certificado_rango = Column("CONTROLACERTIFICADORANGO", Boolean, nullable=False)
    
    
    # empresa = relationship("Empresa", backref="tipos_prestamo")
    # tipo_riesgo_sarf = relationship("TipoRiesgoSARF", backref="tipos_prestamo")
    # tipo_producto_sarf = relationship("TipoProductoSARF", backref="tipos_prestamo")

    # Si en COLOCACION.PRESTAMO existe una FK a CREDITO.TIPO_PRESTAMO(CODIGO),
    # puedes habilitar esta relación:
    prestamos = relationship("Prestamo", back_populates="tipo_prestamo")