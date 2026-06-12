from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric

from app.db.base import Base


class AmortizacionComprasAdecuacionDetalle(Base):
    __tablename__ = "AMORTIZACION_COMPRAS_ADECUACION_DETALLE"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_compra_adecuacion_detalle = Column('IDCOMPRAADECUACIONDETALLE', Integer, ForeignKey('CONTABILIDAD.COMPRAS_ADECUACION_DETALLE.ID'), nullable=False)
    id_agencia = Column('IDAGENCIA', Integer, nullable=False)
    fecha_amortizacion = Column('FECHAAMORTIZACION', DateTime, nullable=False)
    valor_amortizacion = Column('VALORAMORTIZACION', Numeric(18, 2), nullable=False)
    valor_porcentaje = Column('VALORPORCENTAJE', Numeric(18, 2), nullable=False)
    activa = Column('ACTIVA', Boolean, nullable=False)
