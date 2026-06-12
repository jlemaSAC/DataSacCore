from sqlalchemy import (
    Column, Integer, DateTime, DECIMAL, String, ForeignKey, LargeBinary
)
from app.db.base import Base

class PrestamoRubro(Base):
    __tablename__ = "PRESTAMO_RUBRO"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True)
    id_prestamo = Column('IDPRESTAMO', Integer, ForeignKey('COLOCACION.PRESTAMO.ID'), nullable=False)
    id_rubro = Column('IDRUBRO', Integer, ForeignKey('COLOCACION.RUBRO.ID'), nullable=False)
    fecha_inicio = Column('FECHAINICIO', DateTime, nullable=False)
    fecha_fin = Column('FECHAFIN', DateTime, nullable=False)
    numero_cuota = Column('NUMEROCUOTA', Integer, nullable=False)
    proyectado = Column('PROYECTADO', DECIMAL(18, 2), nullable=False)
    calculado = Column('CALCULADO', DECIMAL(18, 6), nullable=False)
    cobrado = Column('COBRADO', DECIMAL(18, 2), nullable=False)
    factor = Column('FACTOR', DECIMAL(18, 2), nullable=False)
    dias_calculo = Column('DIASCALCULO', Integer, nullable=False)
    codigo_estado = Column('CODIGOESTADO', String(10), ForeignKey('COLOCACION.ESTADO_PRESTAMORUBRO.CODIGO'), nullable=False)
    version = Column('VERSION', LargeBinary, nullable=True) 
