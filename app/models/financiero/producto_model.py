from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class Producto(Base):
    __tablename__ = "PRODUCTO"
    __table_args__ = {"schema": "FINANCIERO"}

    codigo = Column("CODIGO", NVARCHAR(50, collation="Modern_Spanish_CI_AS"), primary_key=True, nullable=False)
    codigo_tipo_producto = Column("CODIGOTIPOPRODUCTO", NVARCHAR(50, collation="Modern_Spanish_CI_AS"), ForeignKey("FINANCIERO.TIPO_PRODUCTO.CODIGO"), nullable=False)
    id_moneda = Column("IDMONEDA", Integer, ForeignKey("GENERAL.MONEDA.ID"), nullable=False)
    siglas = Column("SIGLAS", NVARCHAR(10, collation="Modern_Spanish_CI_AS"), nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(150, collation="Modern_Spanish_CI_AS"), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
