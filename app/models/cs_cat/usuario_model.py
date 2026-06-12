from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class UsuarioCsCat(Base):
    __tablename__ = "USUARIO"
    __table_args__ = {"schema": "CS_CAT"}

    codigo = Column("CODIGO", NVARCHAR(50), primary_key=True, nullable=False)
    clave = Column("CLAVE", NVARCHAR(250), nullable=False)
    identificacion = Column("IDENTIFICACION", NVARCHAR(30), nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(150), nullable=False)
    email = Column("EMAIL", NVARCHAR(100), nullable=False)
    cambio_clave_proximo_ingreso = Column("CAMBIOCLAVEPROXIMOINGRESO", Boolean, nullable=False)
    interno = Column("INTERNO", Boolean, nullable=False)
    fecha_creacion = Column("FECHACREACION", DateTime, nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
