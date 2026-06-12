from sqlalchemy import Column, Integer, ForeignKey

from app.db.base import Base


class InversionItemInversionTemporizacion(Base):
    __tablename__ = "INVERSION_ITEMINVERSION_TEMPORIZACION"
    __table_args__ = {"schema": "PORTAFOLIO"}

    id_inversion_item_inversion = Column('IDINVERSIONITEMINVERSION', Integer, ForeignKey('PORTAFOLIO.INVERSION_ITEMINVERSION.ID'), primary_key=True, nullable=False)
    id_temporizacion = Column('IDTEMPORIZACION', Integer, ForeignKey('PORTAFOLIO.TEMPORIZACION_INVERSION_PORTAFOLIO.ID'), nullable=False)


