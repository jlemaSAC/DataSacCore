from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary
from sqlalchemy.dialects.mssql import DECIMAL, NVARCHAR

from app.db.base import Base


class CuentaItemSaldo(Base):
    __tablename__ = "CUENTA_ITEMSALDO"
    __table_args__ = {"schema": "AHORROS"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    numero_cuenta = Column("NUMEROCUENTA", NVARCHAR(50, collation="Modern_Spanish_CI_AS"), ForeignKey("AHORROS.CUENTA.NUMERO"), nullable=False)
    id_item = Column("IDITEM", Integer, ForeignKey("AHORROS.ITEMSALDO.ID"), nullable=False)
    saldo = Column("SALDO", DECIMAL(18, 6), nullable=False)
    version = Column("VERSION", LargeBinary, nullable=False)
    fecha_inicio = Column("FECHAINICIO", DateTime, nullable=False)
    fecha_fin = Column("FECHAFIN", DateTime, nullable=False)
