from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import DECIMAL

from app.db.base import Base


class TipoPrestamoItemAhorroManualRango(Base):
    __tablename__ = "TIPO_PRESTAMO_ITEMAHORRO_MANUALRANGO"
    __table_args__ = {"schema": "CREDITO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_tipo_prestamo_item_ahorro = Column(
        "IDTIPOPRESTAMOITEMAHORRO",
        Integer,
        ForeignKey("CREDITO.TIPO_PRESTAMO_ITEMAHORRO.ID"),
        nullable=False,
    )
    monto_inicio = Column("MONTOINICIO", DECIMAL(18, 2), nullable=False)
    monto_fin = Column("MONTOFIN", DECIMAL(18, 2), nullable=False)
    valor = Column("VALOR", DECIMAL(18, 2), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
