from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import DECIMAL

from app.db.base import Base


class TipoPrestamoItemAhorroPorcentaje(Base):
    __tablename__ = "TIPO_PRESTAMO_ITEMAHORRO_PORCENTAJE"
    __table_args__ = {"schema": "CREDITO"}

    id_tipo_prestamo_item_ahorro = Column(
        "IDTIPOPRESTAMOITEMAHORRO",
        Integer,
        ForeignKey("CREDITO.TIPO_PRESTAMO_ITEMAHORRO.ID"),
        primary_key=True,
        nullable=False,
    )
    porcentaje = Column("PORCENTAJE", DECIMAL(18, 2), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
