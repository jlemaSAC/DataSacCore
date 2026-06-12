from sqlalchemy import Boolean, Column, Integer, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TarifasSriIva(Base):
    __tablename__ = "TARIFAS_SRI_IVA"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    detalle = Column("DETALLE", NVARCHAR(50), nullable=False)
    porcentaje = Column("PORCENTAJE", Numeric(18, 2), nullable=False)
    codigo_porcentaje = Column("CODIGOPORCENTAJE", NVARCHAR(2), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
