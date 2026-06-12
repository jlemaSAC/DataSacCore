from sqlalchemy import (Column, Integer, DECIMAL, Boolean, ForeignKey)
from app.db.base import Base


class SolicitudRubroTransferir(Base):
    __tablename__ = "SOLICITUD_RUBRO_TRANFERIR"
    __table_args__ = {"schema": "CREDITO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True)
    id_solicitud = Column('IDSOLICITUD', Integer, ForeignKey('CREDITO.SOLICITUD_PRESTAMO.ID'), nullable=False)
    id_rubro = Column('IDRUBRO', Integer, ForeignKey('COLOCACION.PRESTAMO_RUBRO.ID'), nullable=False)
    valor = Column('VALOR', DECIMAL(18, 6), nullable=False)
    es_cobro = Column('ESCOBRO', Boolean, nullable=True)
    es_transfiere = Column('ESTRANSFIERE', Boolean, nullable=True)
    es_condona = Column('ESCONDONA', Boolean, nullable=True)

    
