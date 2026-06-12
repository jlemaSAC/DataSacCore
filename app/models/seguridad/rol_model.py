from sqlalchemy import Column, Integer, Boolean
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import relationship
from app.db.base import Base




class Rol(Base):
    __tablename__ = "ROL"
    __table_args__ = {"schema": "SEGURIDAD"}

    codigo = Column("CODIGO", NVARCHAR(50), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(150), nullable=False)
    nivel = Column("NIVEL", Integer, nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)

    usuario_roles = relationship("UsuarioRol", back_populates="rol")