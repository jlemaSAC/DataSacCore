from sqlalchemy import Column, ForeignKey, Integer
from app.db.base import Base


class PrestamoRubroClasificacion(Base):
    __tablename__ = "PRESTAMO_RUBRO_CLASIFICACION"
    __table_args__ = {"schema": "COLOCACION"}

    id_prestamo_rubro = Column("IDPRESTAMORUBRO", Integer, ForeignKey("COLOCACION.PRESTAMO_RUBRO.ID"), primary_key=True, nullable=False)
    id_clasificacion_cartera = Column("IDCLASIFICACIONCARTERA", Integer, ForeignKey("COLOCACION.CLASIFICACION_CARTERA.ID"), nullable=False)
