from sqlalchemy import Boolean, Column
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class SectorVivienda(Base):
    __tablename__ = "SECTORVIVIENDA"
    __table_args__ = {"schema": "SUJETO"}

    codigo = Column("CODIGO", NVARCHAR(50), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(150), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)

