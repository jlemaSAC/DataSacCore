from sqlalchemy import Column, Integer, Boolean
from sqlalchemy.dialects.mssql import VARCHAR

from app.db.base import Base


class TipoItemInversion(Base):
    __tablename__ = "TIPO_ITEMINVERSION"
    __table_args__ = {"schema": "PORTAFOLIO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    nombre = Column('NOMBRE', VARCHAR(50), nullable=False)
    es_capital = Column('ESCAPITAL', Boolean, nullable=False)
    es_interes_calculo = Column('ESINTERESCALCULO', Boolean, nullable=False)
    es_interes_pago = Column('ESINTERESPAGO', Boolean, nullable=False)


