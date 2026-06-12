from sqlalchemy import Column, Integer, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base


class UsuarioRol(Base):
    __tablename__ = "USUARIO_ROL"
    __table_args__ = (
        UniqueConstraint("USUARIOREGISTRO", "CODIGOROL", name="UC_USUARIOROL"),
        {"schema": "SEGURIDAD"},
        
    )

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    usuario_registro = Column('USUARIOREGISTRO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    codigo_rol = Column('CODIGOROL', NVARCHAR(50), ForeignKey('SEGURIDAD.ROL.CODIGO'), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)

    
