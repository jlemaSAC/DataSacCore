from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TransferenciaDebitoCuenta(Base):
    __tablename__ = "TRANSFERENCIA_DEBITOCUENTA"
    __table_args__ = {"schema": "AHORROS"}

    id_transferencia = Column(
        "IDTRANSFERENCIA",
        Integer,
        ForeignKey("AHORROS.TRANSFERENCIA.ID"),
        primary_key=True,
        nullable=False,
    )
    numero_cuenta_debito = Column(
        "NUMEROCUENTADEBITO",
        NVARCHAR(50),
        ForeignKey("AHORROS.CUENTA.NUMERO"),
        nullable=False,
    )
    documento = Column("DOCUMENTO", NVARCHAR(100), nullable=False)
    documento_comision = Column("DOCUMENTOCOMISION", NVARCHAR(100), nullable=False)
