from sqlalchemy import Boolean, Column, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class PeriodoAnio(Base):
    __tablename__ = "PERIODO_ANIO"
    __table_args__ = {"schema": "GENERAL"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(150), nullable=False)
    anio = Column("ANIO", Integer, nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
