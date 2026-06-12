# models/colocacion/prestamo_consolidado.py

from sqlalchemy import Column, Integer, DateTime, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class PrestamoConsolidado(Base):
    __tablename__ = "PRESTAMO_CONSOLIDADO"
    __table_args__ = {"schema": "COLOCACION"}

    id_prestamo = Column("IDPRESTAMO", Integer, ForeignKey("COLOCACION.PRESTAMO.ID"), primary_key=True, nullable=False)
    fecha_ultimo_pago = Column("FECHAULTIMOPAGO", DateTime, nullable=False)
    valor_al_dia = Column("VALORALDIA", DECIMAL(18, 2), nullable=False)
    valor_al_dia_mas_cuota_actual = Column("VALORALDIAMASCUOTACTUAL", DECIMAL(18, 2), nullable=False)
    valor_cancela_prestamo = Column("VALORCANCELAPRESTAMO", DECIMAL(18, 2), nullable=False)
    valor_proyectado_cuota_actual = Column("VALORPROYECTADOCUOTAACTUAL", DECIMAL(18, 2), nullable=False)
    dias_mora_actual = Column("DIASMORAACTUAL", Integer, nullable=False)
    dias_mora = Column("DIASMORA", Integer, nullable=False, default=0)

    prestamos = relationship("Prestamo", back_populates="prestamo_consolidado")
    