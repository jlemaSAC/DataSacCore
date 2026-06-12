from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import DECIMAL

from app.db.base import Base


class TipoPrestamoRubroPorcentajeRango(Base):
    __tablename__ = "TIPO_PRESTAMO_RUBRO_PORCENTAJERANGO"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_tipo_prestamo_rubro = Column(
        "IDTIPOPRESTAMORUBRO",
        Integer,
        ForeignKey("COLOCACION.TIPO_PRESTAMO_RUBRO.ID"),
        nullable=False,
    )
    monto_inicio = Column("MONTOINICIO", DECIMAL(18, 2), nullable=False)
    monto_fin = Column("MONTOFIN", DECIMAL(18, 2), nullable=False)
    porcentaje = Column("PORCENTAJE", DECIMAL(18, 2), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
