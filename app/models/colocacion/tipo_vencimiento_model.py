from sqlalchemy import Boolean, Column, String
from app.db.base import Base


class TipoVencimiento(Base):
    __tablename__ = "TIPO_VENCIMIENTO"
    __table_args__ = {"schema": "COLOCACION"}

    codigo = Column('CODIGO', String(10), primary_key=True, nullable=False)
    nombre = Column('NOMBRE', String(50), nullable=False)
    es_vigente = Column('ESVIGENTE', Boolean, nullable=True)
    es_nodevenga = Column('ESNODEVENGA', Boolean, nullable=True)
    es_vencido = Column('ESVENCIDO', Boolean, nullable=True)
    es_otro = Column('ESOTRO', Boolean, nullable=True)
    activo = Column('ACTIVO', Boolean, nullable=False)
