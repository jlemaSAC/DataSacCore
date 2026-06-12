from sqlalchemy import Boolean, Column, ForeignKey, Integer, text

from app.db.base import Base


class Responsable(Base):
    __tablename__ = "RESPONSABLE"
    __table_args__ = {"schema": "ACTIVOFIJO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_persona = Column('IDPERSONA', Integer, ForeignKey('SUJETO.PERSONA.ID'), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    id_agencia = Column('IDAGENCIA', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False, server_default=text('1'))
