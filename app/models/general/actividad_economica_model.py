from sqlalchemy import Boolean, Column, ForeignKey, Integer, text
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class ActividadEconomica(Base):
    __tablename__ = "ACTIVIDAD_ECONOMICA"
    __table_args__ = {"schema": "GENERAL"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_tipo_actividad = Column(
        "IDTIPOACTIVIDAD", Integer, ForeignKey("GENERAL.TIPO_ACTIVIDAD.ID"), nullable=False
    )
    codigo = Column("CODIGO", NVARCHAR(50), nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(1500), nullable=True)
    activo = Column("ACTIVO", Boolean, nullable=False)
    color = Column("COLOR", NVARCHAR(20), nullable=False, server_default=text("''"))
