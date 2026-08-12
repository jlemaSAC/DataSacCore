from sqlalchemy import Column, ForeignKey, Integer

from app.db.base import Base


class DepositoItemPlazoTemporizacion(Base):
    __tablename__ = "DEPOSITO_ITEMPLAZO_TEMPORIZACION"
    __table_args__ = {"schema": "INVERSION"}

    id_deposito_item_plazo = Column(
        "IDDEPOSITOITEMPLAZO",
        Integer,
        ForeignKey("INVERSION.DEPOSITO_ITEMPLAZO.ID"),
        primary_key=True,
        nullable=False,
    )
    id_temporizacion = Column(
        "IDTEMPORIZACION",
        Integer,
        ForeignKey("INVERSION.TEMPORIZACION_INVERSION.ID"),
        nullable=False,
    )
