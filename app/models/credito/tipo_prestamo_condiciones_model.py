from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoPrestamoCondiciones(Base):
    __tablename__ = "TIPO_PRESTAMO_CONDICIONES"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_prestamo = Column('CODIGOTIPOPRESTAMO', NVARCHAR(30), ForeignKey('CREDITO.TIPO_PRESTAMO.CODIGO'), nullable=False)
    acepta_masculino = Column('ACEPTAMASCULINO', Boolean, nullable=False)
    acepta_femenino = Column('ACEPTAFEMENINO', Boolean, nullable=False)
    acepta_persona_juridica = Column('ACEPTAPERSONAJURIDICA', Boolean, nullable=False)
