from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoPrestamoItemCredito(Base):
    __tablename__ = "TIPO_PRESTAMO_ITEMCREDITO"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_prestamo = Column('CODIGOTIPOPRESTAMO', NVARCHAR(30), ForeignKey('CREDITO.TIPO_PRESTAMO.CODIGO'), nullable=False)
    id_item_credito = Column('IDITEMCREDITO', Integer, ForeignKey('CREDITO.ITEMCREDITO.ID'), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
