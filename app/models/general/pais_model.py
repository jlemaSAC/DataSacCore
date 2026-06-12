from sqlalchemy import Column, Integer, String, Boolean, CHAR, ForeignKey
from app.db.base import Base


class Pais(Base):
    __tablename__ = "PAIS"
    __table_args__ = {"schema": "GENERAL"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo = Column('CODIGO', String(50), nullable=False)
    nombre = Column('NOMBRE', String(150), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    codigo_residencia = Column('CODIGORESIDENCIA', String(10), nullable=False)
    codigo_nacionalidad = Column('CODIGONACIONALIDAD', CHAR(3), ForeignKey('SAC_UAFE.NACIONALIDAD.CODIGO'), nullable=True)
    envia_crs = Column('ENVIACRS', Boolean, nullable=False, default=False)

