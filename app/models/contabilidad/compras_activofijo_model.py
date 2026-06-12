from sqlalchemy import Column, ForeignKey, Integer

from app.db.base import Base


class ComprasActivoFijo(Base):
    __tablename__ = "COMPRAS_ACTIVOFIJO"
    __table_args__ = {"schema": "CONTABILIDAD"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_compra_detalle = Column('IDCOMPRADETALLE', Integer, ForeignKey('CONTABILIDAD.COMPRAS_DETALLE.ID'), nullable=False)
    id_activo_fijo = Column('IDACTIVOFIJO', Integer, ForeignKey('ACTIVOFIJO.ACTIVO.ID'), nullable=False)
