from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoTablaAmortizacion(Base):
    __tablename__ = "TIPO_TABLA_AMORTIZACION"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column('IDEMPRESA', Integer, ForeignKey('GENERAL.EMPRESA.ID'), nullable=False)
    detalle = Column('DETALLE', NVARCHAR(150), nullable=False)
    incrementa_cuota1 = Column('INCREMENTACUOTA1', Boolean, nullable=False)
    cuota_fija = Column('CUOTAFIJA', Boolean, nullable=False)
    alicuota = Column('ALICUOTA', Boolean, nullable=False)
    interes_saldo = Column('INTERES_SALDO', Boolean, nullable=False)
    dia_fijo = Column('DIAFIJO', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
