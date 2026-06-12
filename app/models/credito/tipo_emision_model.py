from sqlalchemy import Column, Boolean, NVARCHAR
from app.db.base import Base


class TipoEmision(Base):
    __tablename__ = "TIPO_EMISION"
    __table_args__ = {"schema": "CREDITO"}

    codigo = Column('CODIGO', NVARCHAR(30), primary_key=True, nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(150), nullable=False)
    normal = Column('NORMAL', Boolean, nullable=False)
    novacion = Column('NOVACION', Boolean, nullable=False)
    refinanciamiento = Column('REFINANCIAMIENTO', Boolean, nullable=False)
    reestructuracion = Column('REESTRUCTURACION', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)


