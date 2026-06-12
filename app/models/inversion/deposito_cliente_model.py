from sqlalchemy import Boolean, Column, ForeignKey, Integer

from app.db.base import Base


class DepositoCliente(Base):
    __tablename__ = "DEPOSITO_CLIENTE"
    __table_args__ = {"schema": "INVERSION"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_deposito = Column('IDDEPOSITO', Integer, ForeignKey('INVERSION.DEPOSITO.ID'), nullable=False)
    id_cliente = Column('IDCLIENTE', Integer, ForeignKey('CLIENTES.CLIENTE.ID'), nullable=False)
    es_principal = Column('ESPRINCIPAL', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
