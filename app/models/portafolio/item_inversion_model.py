from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.mssql import VARCHAR

from app.db.base import Base


class ItemInversion(Base):
    __tablename__ = "ITEMINVERSION"
    __table_args__ = {"schema": "PORTAFOLIO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column('IDEMPRESA', Integer, ForeignKey('GENERAL.EMPRESA.ID'), nullable=False)
    id_tipo_item = Column('IDTIPOITEM', Integer, ForeignKey('PORTAFOLIO.TIPO_ITEMINVERSION.ID'), nullable=False)
    siglas = Column('SIGLAS', VARCHAR(5), nullable=False)
    nombre = Column('NOMBRE', VARCHAR(50), nullable=False)
    se_temporiza = Column('SETEMPORIZA', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)


