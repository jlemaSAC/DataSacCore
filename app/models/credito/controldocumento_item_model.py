from sqlalchemy import Boolean, Column
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class ControlDocumentoItem(Base):
    __tablename__ = "CONTROLDOCUMENTO_ITEM"
    __table_args__ = {"schema": "CREDITO"}

    codigo = Column("CODIGO", NVARCHAR(10), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(250), nullable=False)
    requerido = Column("REQUERIDO", Boolean, nullable=False)
    natural = Column("NATURAL", Boolean, nullable=False)
    juridico = Column("JURIDICO", Boolean, nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
    para_cliente_nuevo = Column("PARACLIENTENUEVO", Boolean, nullable=False)
    para_liquidacion = Column("PARALIQUIDACION", Boolean, nullable=False)
