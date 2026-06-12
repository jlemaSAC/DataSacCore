from sqlalchemy import Boolean, Column
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class AtsTipoComprobante(Base):
    __tablename__ = "ATS_TIPOCOMPROBANTE"
    __table_args__ = {"schema": "CONTABILIDAD"}

    codigo = Column("CODIGO", NVARCHAR(5), primary_key=True, nullable=False)
    descripcion = Column("DESCRIPCION", NVARCHAR(150), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=True)
