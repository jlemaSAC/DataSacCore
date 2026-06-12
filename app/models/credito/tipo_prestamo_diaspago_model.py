from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoPrestamoDiasPago(Base):
    __tablename__ = "TIPO_PRESTAMO_DIASPAGO"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_prestamo = Column('CODIGOTIPOPRESTAMO', NVARCHAR(30), ForeignKey('CREDITO.TIPO_PRESTAMO.CODIGO'), nullable=False)
    dia_inicio = Column('DIAINICIO', Integer, nullable=False)
    dia_fin = Column('DIAFIN', Integer, nullable=False)
