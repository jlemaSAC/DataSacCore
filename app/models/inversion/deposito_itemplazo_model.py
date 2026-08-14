from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class DepositoItemPlazo(Base):
    __tablename__ = "DEPOSITO_ITEMPLAZO"
    __table_args__ = {"schema": "INVERSION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_deposito = Column(
        "IDDEPOSITO", Integer, ForeignKey("INVERSION.DEPOSITO.ID"), nullable=False
    )
    id_item_plazo = Column(
        "IDITEMPLAZO", Integer, ForeignKey("INVERSION.ITEMPLAZO.ID"), nullable=False
    )
    fecha_inicio = Column("FECHAINICIO", DateTime, nullable=False)
    fecha_fin = Column("FECHAFIN", DateTime, nullable=False)
    proyectado = Column("PROYECTADO", Numeric(18, 2), nullable=False)
    calculado = Column("CALCULADO", Numeric(18, 6), nullable=False)
    cobrado = Column("COBRADO", Numeric(18, 2), nullable=False)
    factor = Column("FACTOR", Numeric(18, 2), nullable=False)
    factor_castigo = Column("FACTORCASTIGO", Numeric(18, 2), nullable=False)
    dias_calculo = Column("DIASCALCULO", Integer, nullable=False)
    codigo_estado = Column(
        "CODIGOESTADO",
        NVARCHAR(10),
        ForeignKey("INVERSION.ESTADO_DEPOSITOITEMPLAZO.CODIGO"),
        nullable=False,
    )
    codigo_tipo_cancelacion = Column(
        "CODIGOTIPOCANCELACION",
        NVARCHAR(10),
        ForeignKey("INVERSION.TIPO_CANCELACION.CODIGO"),
        nullable=False,
    )
    se_renueva = Column("SERENUEVA", Boolean, nullable=False)
    version = Column("VERSION", LargeBinary, nullable=False)
