from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoPrestamoItemAhorro(Base):
    __tablename__ = "TIPO_PRESTAMO_ITEMAHORRO"
    __table_args__ = {"schema": "CREDITO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_prestamo = Column(
        "CODIGOTIPOPRESTAMO",
        NVARCHAR(30),
        ForeignKey("CREDITO.TIPO_PRESTAMO.CODIGO"),
        nullable=False,
    )
    id_item_ahorro = Column("IDITEMAHORRO", Integer, ForeignKey("CREDITO.ITEMAHORRO.ID"), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
