from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class ComprasAdecuacionDetalle(Base):
    __tablename__ = "COMPRAS_ADECUACION_DETALLE"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_compra_adecuacion = Column('IDCOMPRAADECUACION', Integer, ForeignKey('CONTABILIDAD.COMPRAS_ADECUACION.ID'), nullable=False)
    id_agencia = Column('IDAGENCIA', Integer, nullable=False)
    fecha_amortizacion = Column('FECHAAMORTIZACION', DateTime, nullable=False)
    valor_amortizacion = Column('VALORAMORTIZACION', Numeric(18, 2), nullable=False)
    codigo_estado = Column('CODIGOESTADO', NVARCHAR(100), nullable=False)
    valor_porcentaje = Column('VALORPORCENTAJE', Numeric(18, 0), nullable=False)
    fecha_proceso = Column('FECHAPROCESO', DateTime, nullable=False)
    activa = Column('ACTIVA', Boolean, nullable=False)
