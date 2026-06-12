from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, Numeric, text
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import relationship

from app.db.base import Base


class Institucion(Base):
    __tablename__ = "INSTITUCION"
    __table_args__ = {"schema": "PORTAFOLIO"}

    codigo = Column("CODIGO", NVARCHAR(5), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(50), nullable=False)
    identificacion = Column("IDENTIFICACION", NVARCHAR(50), nullable=False)
    id_tipo_identificacion = Column(
        "IDTIPOIDENTIFICACION",
        Integer,
        ForeignKey("SUJETO.TIPO_IDENTIFICACION.ID"),
        nullable=False,
    )
    codigo_tipo_institucion = Column(
        "CODIGOTIPOINSTITUCION",
        NVARCHAR(5),
        ForeignKey("PORTAFOLIO.TIPOINSTITUCION.CODIGO"),
        nullable=False,
    )
    id_actividad_economica = Column(
        "IDACTIVIDADECONOMICA",
        Integer,
        ForeignKey("GENERAL.ACTIVIDAD_ECONOMICA.ID"),
        nullable=False,
    )
    codigo_tipo_categoria_calificacion = Column(
        "CODIGOTIPOCATEGORIACALIFICACION",
        NVARCHAR(50),
        ForeignKey("PORTAFOLIO.TIPOCATEGORIACALIFICACION.CODIGO"),
        nullable=False,
    )
    codigo_calificadora_riesgo = Column(
        "CODIGOCALIFICADORARIESGO",
        NVARCHAR(5),
        ForeignKey("PORTAFOLIO.CALIFICADORARIESGO.CODIGO"),
        nullable=False,
    )
    codigo_calificacion_riesgo = Column(
        "CODIGOCALIFICACIONRIESGO",
        NVARCHAR(10),
        ForeignKey("PORTAFOLIO.CALIFICACIONRIESGO.CODIGO"),
        nullable=False,
    )
    fecha_ultima_calificacion = Column("FECHAULTIMACALIFICACION", DateTime, nullable=False)
    codigo_sector = Column(
        "CODIGOSECTOR",
        NVARCHAR(5),
        ForeignKey("PORTAFOLIO.SECTORINVERSION.CODIGO"),
        nullable=False,
    )
    codigo_pais_procedencia = Column(
        "CODIGOPAISPROCEDENCIA",
        NVARCHAR(5),
        ForeignKey("GENERAL.PAIS.CODIGO"),
        nullable=False,
    )
    patrimonio = Column("PATRIMONIO", Numeric(18, 2), nullable=False)
    calidad_activos = Column("CALIDADACTIVOS", Numeric(18, 2), nullable=False)
    rentabilidad = Column("RENTABILIDAD", Numeric(18, 2), nullable=False)
    liquidez = Column("LIQUIDEZ", Numeric(18, 2), nullable=False)
    tiene_custodio = Column("TIENECUSTODIO", Boolean, nullable=False)
    activa = Column("ACTIVA", Boolean, nullable=False)
    id_segmento_inversion = Column(
        "IDSEGMENTOINVERSION",
        Integer,
        ForeignKey("PORTAFOLIO.SEGMENTOINVERSION.ID"),
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    codigo_calificacion_inversion = Column(
        "CODIGOCALIFICACIONINVERSION",
        NVARCHAR(5),
        ForeignKey("PORTAFOLIO.CALIFICACION_RIESGO_INVERSION.CODIGO"),
        nullable=False,
        default="001",
        server_default=text("'001'"),
    )

    sector = relationship("SectorInversion", back_populates="instituciones")
    segmento = relationship("SegmentoInversion", back_populates="instituciones")

