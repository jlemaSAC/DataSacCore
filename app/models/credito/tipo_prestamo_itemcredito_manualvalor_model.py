from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import DECIMAL

from app.db.base import Base


class TipoPrestamoItemCreditoManualValor(Base):
    __tablename__ = "TIPO_PRESTAMO_ITEMCREDITO_MANUALVALOR"
    __table_args__ = {"schema": "CREDITO"}

    id_tipo_prestamo_item_credito = Column('IDTIPOPRESTAMOITEMCREDITO', Integer, ForeignKey('CREDITO.TIPO_PRESTAMO_ITEMCREDITO.ID'), primary_key=True, nullable=False)
    valor = Column('VALOR', DECIMAL(18, 2), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
