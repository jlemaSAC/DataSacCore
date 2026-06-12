from sqlalchemy import Column, ForeignKey, Integer

from app.db.base import Base


class ActivoResponsable(Base):
    __tablename__ = "ACTIVO_RESPONSABLE"
    __table_args__ = {"schema": "ACTIVOFIJO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_activo_fijo = Column("IDACTIVOFIJO", Integer, ForeignKey("ACTIVOFIJO.ACTIVO.ID"), nullable=False)
    id_responsable = Column("IDRESPONSABLE", Integer, ForeignKey("ACTIVOFIJO.RESPONSABLE.ID"), nullable=False)
