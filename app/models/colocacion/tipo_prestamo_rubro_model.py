from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoPrestamoRubro(Base):
    __tablename__ = "TIPO_PRESTAMO_RUBRO"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_prestamo = Column(
        "CODIGOTIPOPRESTAMO",
        NVARCHAR(30),
        ForeignKey("CREDITO.TIPO_PRESTAMO.CODIGO"),
        nullable=False,
    )
    id_rubro = Column("IDRUBRO", Integer, ForeignKey("COLOCACION.RUBRO.ID"), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
