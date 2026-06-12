from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class PersonaTelefono(Base):
    __tablename__ = "PERSONA_TELEFONO"
    __table_args__ = {"schema": "SUJETO"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_persona = Column('IDPERSONA', Integer, ForeignKey('SUJETO.PERSONA.ID'), nullable=False)
    telefono = Column('TELEFONO', NVARCHAR(50, collation='Modern_Spanish_CI_AS'), nullable=False)
    es_telefono_movil = Column('ESTELEFONOMOVIL', Boolean, nullable=False)
    es_principal = Column('ESPRINCIPAL', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)


