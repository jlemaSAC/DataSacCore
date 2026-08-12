from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class DepositoRenovacion(Base):
    __tablename__ = "DEPOSITO_RENOVACION"
    __table_args__ = {"schema": "INVERSION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_deposito_origen = Column(
        "IDDEPOSITOORIGEN", Integer, ForeignKey("INVERSION.DEPOSITO.ID"), nullable=False
    )
    id_deposito_destino = Column(
        "IDDEPOSITODESTINO", Integer, ForeignKey("INVERSION.DEPOSITO.ID"), nullable=False
    )
    valor = Column("VALOR", Numeric(18, 2), nullable=False)
    fecha = Column("FECHA", DateTime, nullable=False)
    fecha_proceso = Column("FECHAPROCESO", DateTime, nullable=False)
    codigo_usuario = Column(
        "CODIGOUSUARIO",
        NVARCHAR(100),
        ForeignKey("SEGURIDAD.USUARIO.USUARIO"),
        nullable=False,
    )
