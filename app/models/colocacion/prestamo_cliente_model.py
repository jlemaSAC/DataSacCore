from sqlalchemy import Column, Integer, Boolean, ForeignKey
from app.db.base import Base

class PrestamoCliente(Base):
    __tablename__ = "PRESTAMO_CLIENTE"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True)
    id_prestamo = Column('IDPRESTAMO', Integer, ForeignKey('COLOCACION.PRESTAMO.ID'), nullable=False)
    id_cliente = Column('IDCLIENTE', Integer, ForeignKey('CLIENTES.CLIENTE.ID'), nullable=False)
    es_principal = Column('ESPRINCIPAL', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
