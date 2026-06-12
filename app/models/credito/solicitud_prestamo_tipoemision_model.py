from sqlalchemy import Column, Integer, NVARCHAR, ForeignKey
from app.db.base import Base


class SolicitudPrestamoTipoEmision(Base):
    __tablename__ = "SOLICITUD_PRESTAMO_TIPOEMISION"
    __table_args__ = {"schema": "CREDITO"}

    id_solicitud = Column('IDSOLICITUD', Integer, ForeignKey('CREDITO.SOLICITUD_PRESTAMO.ID'), primary_key=True, nullable=False)
    codigo_tipo_emision = Column('CODIGOTIPOEMISION', NVARCHAR(30), ForeignKey('CREDITO.TIPO_EMISION.CODIGO'), nullable=False)

    # Si tienes el modelo SolicitudPrestamo, aquí va la relación
