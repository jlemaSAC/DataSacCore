from sqlalchemy import Column, String, Boolean
from app.db.base import Base

class EstadoPrestamo(Base):
    __tablename__ = "ESTADO_PRESTAMO"
    __table_args__ = {"schema": "COLOCACION"}

    codigo = Column('CODIGO', String(10), primary_key=True, nullable=False)
    nombre = Column('NOMBRE', String(150), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    codigo_sarf = Column('CODIGOSARF', String(1), nullable=True)