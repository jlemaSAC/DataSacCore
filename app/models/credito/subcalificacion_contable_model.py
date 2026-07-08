from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class SubcalificacionContable(Base):
    __tablename__ = "SUBCALIFICACION_CONTABLE"
    __table_args__ = {"schema": "CREDITO"}

    codigo = Column("CODIGO", NVARCHAR(30), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(150), nullable=False)
    codigo_calificacion_contable = Column("CODIGOCALIFICACIONCONTABLE", NVARCHAR(30), ForeignKey("CREDITO.CALIFICACION_CONTABLE.CODIGO"), nullable=False)
