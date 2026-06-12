from sqlalchemy import Column, Integer, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import relationship

from app.db.base import Base


class SegmentoInversion(Base):
    __tablename__ = "SEGMENTOINVERSION"
    __table_args__ = {"schema": "PORTAFOLIO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_sector_inversion = Column(
        "CODIGOSECTORINVERSION",
        NVARCHAR(5),
        ForeignKey("PORTAFOLIO.SECTORINVERSION.CODIGO"),
        nullable=False,
    )
    nombre = Column("NOMBRE", NVARCHAR(50), nullable=False)
    porcentaje = Column("PORCENTAJE", Numeric(18, 2), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)

    sector = relationship("SectorInversion", back_populates="segmentos")
    instituciones = relationship("Institucion", back_populates="segmento")

