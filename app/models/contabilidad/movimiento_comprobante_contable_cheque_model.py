from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR, VARCHAR
from app.db.base import Base


class MovimientoComprobanteContableCheque(Base):
    __tablename__ = "MOVIMIENTOCOMPROBANTECONTABLE_CHEQUE"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_movimiento_contable = Column('IDMOVIMIENTOCONTABLE', Integer, ForeignKey('CONTABILIDAD.MOVIMIENTOCOMPROBANTECONTABLE.ID'), nullable=False)
    numero_cheque = Column('NUMEROCHEQUE', Integer, nullable=False)
    beneficiario = Column('BENEFICIARIO', NVARCHAR(250), nullable=False)
    lugar = Column('LUGAR', NVARCHAR(100), nullable=False)
    fecha = Column('FECHA', DateTime, nullable=False)
    valor = Column('VALOR', Numeric(18, 2), nullable=False)
    valor_en_letras = Column('VALORENLETRAS', VARCHAR(200), nullable=False)
    activa = Column('ACTIVA', Boolean, nullable=False)

    # Relación muchos-a-uno con el movimiento contable
