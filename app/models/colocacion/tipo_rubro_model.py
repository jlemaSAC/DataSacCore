# models/colocacion/tipo_rubro_model.py

from sqlalchemy import Column, Boolean
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base

class TipoRubro(Base):
    __tablename__ = "TIPO_RUBRO"
    __table_args__ = {"schema": "COLOCACION"}

    codigo = Column('CODIGO', NVARCHAR(10), primary_key=True, nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(150), nullable=False)

    es_capital = Column('ESCAPITAL', Boolean, nullable=False)
    es_tasa = Column('ESTASA', Boolean, nullable=False)
    es_mora = Column('ESMORA', Boolean, nullable=False)
    es_seguro = Column('ESSEGURO', Boolean, nullable=False)
    es_castigo = Column('ESCASTIGO', Boolean, nullable=False)
    es_adicional = Column('ESADICIONAL', Boolean, nullable=False)
    es_judicial = Column('ESJUDICIAL', Boolean, nullable=False)
    es_prejudicial = Column('ESPREJUDICIAL', Boolean, nullable=False)
    es_medico = Column('ESMEDICO', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    es_ahorros = Column('ESAHORROS', Boolean, nullable=False)

