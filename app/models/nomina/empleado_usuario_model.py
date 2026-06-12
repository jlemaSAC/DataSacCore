from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base


class EmpleadoUsuario(Base):
    __tablename__ = "EMPLEADO_USUARIO"
    __table_args__ = {"schema": "NOMINA"}

    id_empleado = Column('IDEMPLEADO', Integer, nullable=True)
    codigo_usuario = Column('CODIGOUSUARIO', NVARCHAR(100), ForeignKey('SEGURIDAD.USUARIO.USUARIO'), primary_key=True, nullable=False)
    id_funcionario = Column('IDFUNCIONARIO', Integer, ForeignKey('NOMINA.FUNCIONARIO.ID'), nullable=False)

