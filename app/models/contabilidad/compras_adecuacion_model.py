from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class ComprasAdecuacion(Base):
    __tablename__ = "COMPRAS_ADECUACION"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_compra = Column(
        "IDCOMPRA",
        Integer,
        ForeignKey("CONTABILIDAD.COMPRAS.ID"),
        nullable=False,
    )
    id_agencia = Column("IDAGENCIA", Integer, nullable=False)
    valor_compra = Column("VALORCOMPRA", Numeric(18, 2), nullable=False)
    fecha_compra = Column("FECHACOMPRA", DateTime, nullable=False)
    codigo_usuario = Column(
        "CODIGOUSUARIO",
        NVARCHAR(100),
        ForeignKey("SEGURIDAD.USUARIO.USUARIO"),
        nullable=False,
    )
    es_prorrateo = Column("ESPRORRATEO", Boolean, nullable=False)
    fecha = Column("FECHA", DateTime, nullable=False)
    activa = Column("ACTIVA", Boolean, nullable=False)
