from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class DepositoFrecuenciaPago(Base):
    __tablename__ = "DEPOSITO_FRECUENCIA_PAGO"
    __table_args__ = {"schema": "INVERSION"}

    id_deposito = Column(
        "IDDEPOSITO",
        Integer,
        ForeignKey("INVERSION.DEPOSITO.ID"),
        primary_key=True,
        nullable=False,
    )
    codigo_frecuencia_pago = Column(
        "CODIGOFRECUENCIAPAGO",
        NVARCHAR(10),
        ForeignKey("INVERSION.FRECUENCIA_PAGO.CODIGO"),
        nullable=False,
    )
