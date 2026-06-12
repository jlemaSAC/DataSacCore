from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class RubroCalculoAdicional(Base):
    __tablename__ = "RUBRO_CALCULOADICIONAL"
    __table_args__ = {"schema": "COLOCACION"}

    id_rubro = Column("IDRUBRO", Integer, ForeignKey("COLOCACION.RUBRO.ID"), primary_key=True, nullable=False)
    metodo_calculo = Column("METODOCALCULO", NVARCHAR(100), nullable=False)
