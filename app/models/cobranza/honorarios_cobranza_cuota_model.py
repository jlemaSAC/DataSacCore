from sqlalchemy import Column, Integer, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import Base


class HonorariosCobranzaCuota(Base):
    __tablename__ = "HONORARIOS_COBRANZA_CUOTA"
    __table_args__ = {"schema": "COBRANZA"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_honorarios_cobranza = Column(
        "IDHONORARIOSCOBRANZA",
        Integer,
        ForeignKey("COBRANZA.HONORARIOS_COBRANZA.ID"),
        nullable=False,
    )
    dias_mora_inicio = Column("DIASMORAINICIO", Integer, nullable=False)
    dias_mora_fin = Column("DIASMORAFIN", Integer, nullable=False)
    honorario = Column("HONORARIO", DECIMAL(18, 2), nullable=False)
    porcentaje_honorario = Column("PORCENTAJEHONORARIO", DECIMAL(18, 2), nullable=False)

    # Relaciones
    honorarios_cobranza = relationship("HonorariosCobranza", back_populates="cuotas")
