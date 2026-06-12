from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, text
from sqlalchemy.dialects.mssql import DECIMAL, NVARCHAR

from app.db.base import Base


class TipoPrestamoEncaje(Base):
    __tablename__ = "TIPO_PRESTAMO_ENCAJE"
    __table_args__ = {"schema": "CREDITO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_prestamo = Column(
        "CODIGOTIPOPRESTAMO",
        NVARCHAR(30),
        ForeignKey("CREDITO.TIPO_PRESTAMO.CODIGO"),
        nullable=False,
    )
    codigo_tipo_cuenta = Column(
        "CODIGOTIPOCUENTA",
        NVARCHAR(50),
        ForeignKey("AHORROS.TIPO_CUENTA.CODIGO"),
        nullable=False,
    )
    monto_inicio = Column("MONTOINICIO", DECIMAL(18, 2), nullable=False)
    monto_fin = Column("MONTOFIN", DECIMAL(18, 2), nullable=False)
    relacion = Column("RELACION", DECIMAL(18, 2), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
    tasa_encaje = Column("TASAENCAJE", DECIMAL(18, 2), nullable=False, server_default=text("0"))
    fecha_sistema = Column("FECHASISTEMA", DateTime, nullable=False, server_default=text("'20240801'"))
    fecha_proceso = Column("FECHAPROCESO", DateTime, nullable=False, server_default=text("'20240801'"))
