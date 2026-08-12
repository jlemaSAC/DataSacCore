from sqlalchemy import Boolean, Column
from sqlalchemy.dialects.mssql import CHAR, NVARCHAR

from app.db.base import Base


class EstadoDeposito(Base):
    __tablename__ = "ESTADO_DEPOSITO"
    __table_args__ = {"schema": "INVERSION"}

    codigo = Column("CODIGO", NVARCHAR(10), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(20), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
    codigo_sarf = Column("CODIGOSARF", CHAR(1), nullable=True)
