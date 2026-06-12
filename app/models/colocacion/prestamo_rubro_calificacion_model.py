from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base


class PrestamoRubroCalificacion(Base):
    __tablename__ = "PRESTAMO_RUBRO_CALIFICACION"
    __table_args__ = {"schema": "COLOCACION"}

    id_prestamo_rubro = Column('IDPRESTAMORUBRO', Integer, ForeignKey('COLOCACION.PRESTAMO_RUBRO.ID'), primary_key=True, nullable=False)
    dias_mora = Column('DIASMORA', Integer, nullable=False)
    calificacion = Column('CALIFICACION', NVARCHAR(5), nullable=False)
