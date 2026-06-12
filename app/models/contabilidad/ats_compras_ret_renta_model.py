from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric

from app.db.base import Base


class AtsComprasRetRenta(Base):
    __tablename__ = "ATS_COMPRAS_RET_RENTA"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_ats_compras = Column(
        "IDATSCOMPRAS",
        Integer,
        ForeignKey("CONTABILIDAD.ATS_COMPRAS.ID"),
        nullable=False,
    )
    id_retencion_renta = Column(
        "IDRETENCIONRENTA",
        Integer,
        ForeignKey("CONTABILIDAD.ATS_RETENCION_RENTA.ID"),
        nullable=False,
    )
    base_imponible = Column("BASEIMPONIBLE", Numeric(18, 2), nullable=False)
    porcentaje = Column("PORCENTAJE", Numeric(18, 2), nullable=False)
    valor_retencion = Column("VALORRETENCION", Numeric(18, 2), nullable=False)
    fecha_pago_dividendo = Column("FECHAPAGODIVIDENDO", DateTime, nullable=True)
    impuesto_pagado_dividendo = Column("IMPUESTOPAGADODIVIDENDO", Numeric(18, 2), nullable=False)
    ano_ultimo_dividendo = Column("ANOULTIMODIVIDENDO", Integer, nullable=False)
