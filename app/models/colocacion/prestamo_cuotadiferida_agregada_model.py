from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import relationship

from app.db.base import Base


class PrestamoCuotaDiferidaAgregada(Base):
    __tablename__ = "PRESTAMO_CUOTADIFERIDA_AGREGADA"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_prestamo = Column("IDPRESTAMO", Integer, ForeignKey("COLOCACION.PRESTAMO.ID"), nullable=False)
    comentario = Column("COMENTARIO", NVARCHAR(1000), nullable=False)
    fecha_sistema = Column("FECHASISTEMA", DateTime, nullable=False)
    fecha_proceso = Column("FECHAPROCESO", DateTime, nullable=False)
    codigo_usuario = Column("CODIGOUSUARIO", NVARCHAR(100), ForeignKey("SEGURIDAD.USUARIO.USUARIO"), nullable=False)

    prestamo = relationship("Prestamo")
    usuario = relationship("Usuario")
