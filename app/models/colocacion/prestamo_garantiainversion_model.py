from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class PrestamoGarantiaInversion(Base):
    __tablename__ = "PRESTAMO_GARANTIAINVERSION"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True, nullable=False)
    id_prestamo = Column('IDPRESTAMO', Integer, ForeignKey('COLOCACION.PRESTAMO.ID'), nullable=False)
    id_inversion = Column('IDINVERSION', Integer, ForeignKey('INVERSION.DEPOSITO.ID'), nullable=False)
    codigo_estado = Column('CODIGOESTADO', NVARCHAR(10), ForeignKey('COLOCACION.ESTADO_PRESTAMO_GARANTIA.CODIGO'), nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)

