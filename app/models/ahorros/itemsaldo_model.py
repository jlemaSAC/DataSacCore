from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class ItemSaldo(Base):
    __tablename__ = "ITEMSALDO"
    __table_args__ = {"schema": "AHORROS"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column("IDEMPRESA", Integer, ForeignKey("GENERAL.EMPRESA.ID"), nullable=False)
    id_tipo_item = Column("IDTIPOITEM", Integer, ForeignKey("AHORROS.TIPO_ITEMSALDO.ID"), nullable=False)
    siglas = Column("SIGLAS", NVARCHAR(10, collation="Modern_Spanish_CI_AS"), nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(100, collation="Modern_Spanish_CI_AS"), nullable=False)
    suma_saldo = Column("SUMASALDO", Boolean, nullable=False)
    acredita_prestamo = Column("ACREDITAPRESTAMO", Boolean, nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
