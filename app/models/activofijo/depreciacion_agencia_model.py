from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class DepreciacionAgencia(Base):
    __tablename__ = "DEPRECIACION_AGENCIA"
    __table_args__ = {"schema": "ACTIVOFIJO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_agencia = Column("IDAGENCIA", Integer, ForeignKey("GENERAL.AGENCIA.ID"), nullable=False)
    fecha_calculo = Column("FECHACALCULO", DateTime, nullable=False)
    fecha = Column("FECHA", DateTime, nullable=False)
    fecha_proceso = Column("FECHAPROCESO", DateTime, nullable=False)
    codigo_usuario = Column(
        "CODIGOUSUARIO",
        NVARCHAR(100),
        ForeignKey("SEGURIDAD.USUARIO.USUARIO"),
        nullable=False,
    )
