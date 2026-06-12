from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric

from app.db.base import Base


class AtsComprasRetIva(Base):
    __tablename__ = "ATS_COMPRAS_RET_IVA"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_ats_compras = Column(
        "IDATSCOMPRAS",
        Integer,
        ForeignKey("CONTABILIDAD.ATS_COMPRAS.ID"),
        nullable=False,
    )
    id_retencion_iva = Column(
        "IDRETENCIONIVA",
        Integer,
        ForeignKey("CONTABILIDAD.ATS_RETENCION_IVA.ID"),
        nullable=False,
    )
    bienes = Column("BIENES", Boolean, nullable=False)
    porcentaje = Column("PORCENTAJE", Numeric(18, 2), nullable=False)
