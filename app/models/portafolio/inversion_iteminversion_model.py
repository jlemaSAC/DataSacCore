from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey, Numeric, LargeBinary
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import relationship

from app.db.base import Base


class InversionItemInversion(Base):
    __tablename__ = "INVERSION_ITEMINVERSION"
    __table_args__ = {"schema": "PORTAFOLIO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_inversion = Column(
        "IDINVERSION",
        Integer,
        ForeignKey("PORTAFOLIO.INVERSIONPORTAFOLIO.ID"),
        nullable=False,
    )
    id_item_inversion = Column(
        "IDITEMINVERSION",
        Integer,
        ForeignKey("PORTAFOLIO.ITEMINVERSION.ID"),
        nullable=False,
    )
    codigo_estado = Column(
        "CODIGOESTADO",
        NVARCHAR(5),
        ForeignKey("PORTAFOLIO.ESTADOITEMINVERSION.CODIGO"),
        nullable=False,
    )
    fecha_inicio = Column("FECHAINICIO", DateTime, nullable=False)
    fecha_fin = Column("FECHAFIN", DateTime, nullable=False)
    proyectado = Column("PROYECTADO", Numeric(18, 2), nullable=False)
    calculado = Column("CALCULADO", Numeric(18, 2), nullable=False)
    cobrado = Column("COBRADO", Numeric(18, 2), nullable=False)
    factor = Column("FACTOR", Numeric(18, 2), nullable=False)
    factor_castigo = Column("FACTORCASTIGO", Numeric(18, 2), nullable=True)
    dias_calculo = Column("DIASCALCULO", Numeric(18, 2), nullable=False)
    saldo = Column("SALDO", Numeric(18, 2), nullable=False)
    version = Column("VERSION", LargeBinary, nullable=False)

    inversion = relationship("InversionPortafolio", back_populates="items")
    item = relationship("ItemInversion", back_populates="inversion_items")
    temporizacion = relationship(
        "InversionItemInversionTemporizacion",
        back_populates="inversion_item",
        uselist=False,
    )

