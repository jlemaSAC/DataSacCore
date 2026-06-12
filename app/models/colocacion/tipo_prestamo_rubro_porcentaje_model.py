from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import DECIMAL

from app.db.base import Base


class TipoPrestamoRubroPorcentaje(Base):
    __tablename__ = "TIPO_PRESTAMO_RUBRO_PORCENTAJE"
    __table_args__ = {"schema": "COLOCACION"}

    id_tipo_prestamo_rubro = Column(
        "IDTIPOPRESTAMORUBRO",
        Integer,
        ForeignKey("COLOCACION.TIPO_PRESTAMO_RUBRO.ID"),
        primary_key=True,
        nullable=False,
    )
    porcentaje = Column("PORCENTAJE", DECIMAL(18, 4), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
