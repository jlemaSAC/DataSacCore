from sqlalchemy import (
    Column, Integer, DECIMAL, Boolean, ForeignKey
)
from app.db.base import Base


class SolicitudPrestamoCancelaPrestamo(Base):
    __tablename__ = "SOLICITUD_PRESTAMO_CANCELAPRESTAMO"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True)
    id_solicitud_prestamo = Column('IDSOLICITUDPRESTAMO', Integer, ForeignKey('CREDITO.SOLICITUD_PRESTAMO.ID'), nullable=False)
    id_prestamo = Column('IDPRESTAMO', Integer, ForeignKey('COLOCACION.PRESTAMO.ID'), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    prorratea_saldo = Column('PRORRATEASALDO', Boolean, nullable=True, default=False)
    saldo_capital = Column('SALDOCAPITAL', DECIMAL(18, 2), nullable=True)
    otros_rubros = Column('OTROSRUBROS', DECIMAL(18, 2), nullable=True)
    prorrateo_cuota = Column('PRORRATEOCUOTA', Boolean, nullable=True, default=False)
    es_alivio_financiero = Column('ESALIVIOFINANCIERO', Boolean, nullable=True)
    numero_cuota_prorrateo = Column('NUMEROCUOTAPRORRATEO', Integer, nullable=True)

    # Relaciones (si las vas a usar)
