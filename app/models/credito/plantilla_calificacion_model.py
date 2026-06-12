from sqlalchemy import Boolean, Column
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class PlantillaCalificacion(Base):
    __tablename__ = "PLANTILLA_CALIFICACION"
    __table_args__ = {"schema": "CREDITO"}

    codigo = Column('CODIGO', NVARCHAR(30), primary_key=True, nullable=False)
    detalle = Column('DETALLE', NVARCHAR(150), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
