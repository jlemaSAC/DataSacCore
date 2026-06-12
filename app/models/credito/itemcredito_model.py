from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class ItemCredito(Base):
    __tablename__ = "ITEMCREDITO"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column('IDEMPRESA', Integer, ForeignKey('GENERAL.EMPRESA.ID'), nullable=False)
    id_tipo_item = Column('IDTIPOITEM', Integer, ForeignKey('CREDITO.TIPO_ITEMCREDITO.ID'), nullable=False)
    siglas = Column('SIGLAS', NVARCHAR(10), nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(100), nullable=False)
    incrementa_saldo = Column('INCREMENTASALDO', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
