from sqlalchemy import Column, ForeignKey, Index, Integer
from sqlalchemy.dialects.mssql import DECIMAL, NVARCHAR

from app.db.base import Base


class CausalMovimientoTransaccion(Base):
    __tablename__ = "CAUSAL_MOVIMIENTOTRANSACCION"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_movimiento_transaccion_detalle = Column(
        "IDMOVIMIENTOTRANSACCIONDETALLE",
        Integer,
        ForeignKey("FINANCIERO.MOVIMIENTO_TRANSACCION_DETALLE.ID"),
        nullable=False,
    )
    codigo_causal = Column(
        "CODIGOCAUSAL",
        NVARCHAR(50),
        ForeignKey("CONTABILIDAD.CAUSAL.CODIGO"),
        nullable=False,
    )
    id_forma_pago = Column(
        "IDFORMAPAGO",
        Integer,
        ForeignKey("FINANCIERO.FORMA_PAGO.ID"),
        nullable=False,
    )
    concepto = Column("CONCEPTO", NVARCHAR(500), nullable=False)
    valor = Column("VALOR", DECIMAL(18, 2), nullable=False)


Index(
    "IX_CAUSAL_MOVIMIENTOTRANSACCION_IDMOVIMIENTOTRANSACCIONDETALLE",
    CausalMovimientoTransaccion.id_movimiento_transaccion_detalle,
    mssql_include=["CODIGOCAUSAL", "VALOR"],
)
