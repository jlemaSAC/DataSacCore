from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class PrestamoGarantiaHipotecaria(Base):
    __tablename__ = "PRESTAMO_GARANTIAHIPOTECARIA"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_prestamo = Column('IDPRESTAMO', Integer, ForeignKey('COLOCACION.PRESTAMO.ID'), nullable=False)
    id_garantia_hipotecaria = Column('IDGARANTIAHIPOTECARIA', Integer, ForeignKey('CREDITO.GARANTIAHIPOTECARIA.ID'), nullable=False)
    codigo_estado_garantia = Column('CODIGOESTADOGARANTIA', NVARCHAR(10), ForeignKey('COLOCACION.ESTADO_PRESTAMO_GARANTIA.CODIGO'), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
