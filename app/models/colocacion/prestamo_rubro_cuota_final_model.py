# models/colocacion/prestamo_rubro_cuota_final_model.py

from sqlalchemy import Column, Integer, DateTime, DECIMAL, ForeignKey, text

from app.db.base import Base


class PrestamoRubroCuotaFinal(Base):
    __tablename__ = "PRESTAMO_RUBRO_CUOTA_FINAL"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_prestamo_rubro_anterior = Column('IDPRESTAMORUBROANTERIOR', Integer, ForeignKey('COLOCACION.PRESTAMO_RUBRO.ID'), nullable=False)
    id_prestamo_rubro_nuevo = Column('IDPRESTAMORUBRONUEVO', Integer, ForeignKey('COLOCACION.PRESTAMO_RUBRO.ID'), nullable=False)
    valor_proyectado = Column('VALORPROYECTADO', DECIMAL(18, 2), nullable=False)
    fecha_inicio = Column('FECHAINICIO', DateTime, nullable=False, server_default=text('sysutcdatetime()'))
    fecha_fin = Column('FECHAFIN', DateTime, nullable=False, server_default=text("'9999-12-31 23:59:59.9999999'"))
