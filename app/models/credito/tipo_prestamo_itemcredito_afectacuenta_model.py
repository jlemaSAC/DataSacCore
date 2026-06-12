from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoPrestamoItemCreditoAfectaCuenta(Base):
    __tablename__ = "TIPO_PRESTAMO_ITEMCREDITO_AFECTACUENTA"
    __table_args__ = {"schema": "CREDITO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_tipo_prestamo_item_credito = Column(
        "IDTIPOPRESTAMOITEMCREDITO",
        Integer,
        ForeignKey("CREDITO.TIPO_PRESTAMO_ITEMCREDITO.ID"),
        nullable=False,
    )
    codigo_tipo_cuenta = Column(
        "CODIGOTIPOCUENTA",
        NVARCHAR(50),
        ForeignKey("AHORROS.TIPO_CUENTA.CODIGO"),
        nullable=False,
    )
    id_item_saldo = Column("IDITEMSALDO", Integer, ForeignKey("AHORROS.ITEMSALDO.ID"), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
