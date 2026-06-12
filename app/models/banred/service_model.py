from sqlalchemy import Boolean, Column
from sqlalchemy.dialects.mssql import NVARCHAR, VARCHAR

from app.db.base import Base


class BanredService(Base):
    __tablename__ = "SERVICE"
    __table_args__ = {"schema": "BANRED"}

    codigo = Column("CODIGO", VARCHAR(5), primary_key=True, nullable=False)
    servicio = Column("SERVICIO", VARCHAR(15), nullable=False)
    descripcion = Column("DESCRIPCION", VARCHAR(50), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
    tipo_cuenta_transaccion = Column("TIPOCUENTATRANSACCION", NVARCHAR(4), nullable=True)
