from sqlalchemy import Column, ForeignKey, Integer

from app.db.base import Base


class EstructuraPadre(Base):
    __tablename__ = "ESTRUCTURA_PADRE"
    __table_args__ = {"schema": "ACTIVOFIJO"}

    id_estructura = Column('IDESTRUCTURA', Integer, ForeignKey('ACTIVOFIJO.ESTRUCTURA.ID'), primary_key=True, nullable=False)
    id_estructura_padre = Column('IDESTRUCTURAPADRE', Integer, ForeignKey('ACTIVOFIJO.ESTRUCTURA.ID'), nullable=True)
