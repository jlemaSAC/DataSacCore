from sqlalchemy import Column, DateTime, ForeignKey, Integer
from app.db.base import Base

class EmpresaCierreHistorico(Base):
    __tablename__ = "EMPRESA_CIERREHISTORICO"
    __table_args__ = {"schema": "GENERAL"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column('IDEMPRESA', Integer, ForeignKey('GENERAL.EMPRESA.ID'), nullable=False)

    fecha_sistema = Column('FECHASISTEMA', DateTime, nullable=False)
    fecha_cierre_vista = Column('FECHACIERREVISTA', DateTime, nullable=False)
    fecha_cierre_plazo = Column('FECHACIERREPLAZO', DateTime, nullable=False)
    fecha_cierre_colocacion = Column('FECHACIERRECOLOCACION', DateTime, nullable=False)
    fecha_cierre_cajas = Column('FECHACIERRECAJAS', DateTime, nullable=False)
    fecha_cierre_obligaciones = Column('FECHACIERREOBLIGACIONES', DateTime, nullable=False)
    fecha_cierre_portafolio = Column('FECHACIERREPORTAFOLIO', DateTime, nullable=False)
    fecha_cierre_nomina = Column('FECHACIERRENOMINA', DateTime, nullable=False)
    fecha_cierre_activos = Column('FECHACIERREACTIVOS', DateTime, nullable=False)