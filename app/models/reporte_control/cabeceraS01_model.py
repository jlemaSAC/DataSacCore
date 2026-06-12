# models/reporte_control/cabecera_s01.py

from sqlalchemy import Column, Integer, String, DateTime
from app.db.base import Base

class CabeceraS01(Base):
    __tablename__ = "CABECERA_S01"
    __table_args__ = {"schema": "REPORTECONTROL"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True)
    codigo_estructura = Column('CODIGOESTRUCTURA', String(5), nullable=False)
    ruc = Column('RUC', String(13), nullable=False)
    fecha_corte = Column('FECHACORTE', DateTime, nullable=False)
    numero_registros = Column('NUMEROREGISTROS', Integer, nullable=False)
    codigo_usuario_genera = Column('CODIGOUSUARIOGENERA', String(100), nullable=False)
    fecha_sistema_genera = Column('FECHASISTEMAGENERA', DateTime, nullable=False)
    fecha_proceso_genera = Column('FECHAPROCESOGENERA', DateTime, nullable=False)

