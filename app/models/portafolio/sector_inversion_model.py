from sqlalchemy import Column, Boolean, Numeric, text
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class SectorInversion(Base):
    __tablename__ = "SECTORINVERSION"
    __table_args__ = {"schema": "PORTAFOLIO"}

    codigo = Column('CODIGO', NVARCHAR(5), primary_key=True, nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(50), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    porcentaje = Column('PORCENTAJE', Numeric(18, 2), nullable=False, default=0, server_default=text('0'))


