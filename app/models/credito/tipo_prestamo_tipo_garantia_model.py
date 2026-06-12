from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import DECIMAL, NVARCHAR

from app.db.base import Base


class TipoPrestamoTipoGarantia(Base):
    __tablename__ = "TIPO_PRESTAMO_TIPO_GARANTIA"
    __table_args__ = {"schema": "CREDITO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_prestamo = Column(
        "CODIGOTIPOPRESTAMO",
        NVARCHAR(30),
        ForeignKey("CREDITO.TIPO_PRESTAMO.CODIGO"),
        nullable=False,
    )
    codigo_tipo_garantia = Column(
        "CODIGOTIPOGARANTIA",
        NVARCHAR(30),
        ForeignKey("CREDITO.TIPO_GARANTIA.CODIGO"),
        nullable=False,
    )
    cantidad_minimo = Column("CANTIDADMINIMO", Integer, nullable=False)
    cantidad_maximo = Column("CANTIDADMAXIMO", Integer, nullable=False)
    monto_minimo = Column("MONTOMINIMO", DECIMAL(18, 2), nullable=False)
    monto_maximo = Column("MONTOMAXIMO", DECIMAL(18, 2), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
    score_minimo = Column("SCOREMINIMO", Integer, nullable=False)
    score_maximo = Column("SCOREMAXIMO", Integer, nullable=False)
