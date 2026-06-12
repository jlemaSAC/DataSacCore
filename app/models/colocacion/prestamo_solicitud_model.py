from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class PrestamoSolicitud(Base):
    __tablename__ = "PRESTAMO_SOLICITUD"
    __table_args__ = {"schema": "COLOCACION"}

    id_prestamo = Column("IDPRESTAMO",Integer,ForeignKey("COLOCACION.PRESTAMO.ID"),primary_key=True,nullable=False)
    id_solicitud = Column("IDSOLICITUD",Integer,ForeignKey("CREDITO.SOLICITUD_PRESTAMO.ID"),nullable=False)

    prestamos = relationship("Prestamo",back_populates="prestamos_solicitud")
    # solicitud = relationship("SolicitudPrestamo",back_populates="prestamos_solicitud")