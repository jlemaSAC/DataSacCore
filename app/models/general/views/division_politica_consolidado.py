from sqlalchemy import NVARCHAR, Column, Integer
from app.db.base import Base


class DivisionPoliticaConsolidado(Base):
    __tablename__ = "DIVISIONPOLITICA_CONSOLIDADO"
    __table_args__ = {"schema": "GENERAL"}

    id_division_nivel_bajo = Column('IDDIVISIONNIVELBAJO', Integer, primary_key=True, nullable=False)
    provincia = Column('PROVINCIA', NVARCHAR(150), nullable=False)
    canton = Column('CANTON', NVARCHAR(150), nullable=False)
    parroquia = Column('PARROQUIA', NVARCHAR(150), nullable=False)