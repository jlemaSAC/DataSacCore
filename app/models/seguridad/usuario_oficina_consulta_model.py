from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base


class UsuarioOficinaConsulta(Base):
    __tablename__ = "USUARIO_OFICINACONSULTA"
    __table_args__ = {"schema": "SEGURIDAD"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_usuario = Column('CODIGOUSUARIO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), nullable=False)
    id_agencia = Column('IDAGENCIA', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)

