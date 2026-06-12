from sqlalchemy import Boolean, Column
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class CondicionActivo(Base):
    __tablename__ = "CONDICION_ACTIVO"
    __table_args__ = {"schema": "ACTIVOFIJO"}

    codigo = Column("CODIGO", NVARCHAR(10), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(50), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
