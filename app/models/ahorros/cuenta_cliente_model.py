from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import relationship
from app.db.base import Base


class CuentaCliente(Base):
    __tablename__ = "CUENTA_CLIENTE"
    __table_args__ = {"schema": "AHORROS"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    numero_cuenta = Column(
        "NUMEROCUENTA",
        NVARCHAR(50, collation="Modern_Spanish_CI_AS"),
        ForeignKey("AHORROS.CUENTA.NUMERO"),
        nullable=False,
    )
    id_cliente = Column("IDCLIENTE", Integer, ForeignKey("CLIENTES.CLIENTE.ID"), nullable=False)
    principal = Column("PRINCIPAL", Boolean, nullable=False)

    # Relaciones mínimas
    clientes = relationship("Cliente", back_populates="cuentas_clientes")
    cuentas = relationship("Cuenta", back_populates="cuentas_clientes")
