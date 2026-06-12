from sqlalchemy import Boolean, Column, DECIMAL, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class CalificacionContable(Base):
    __tablename__ = "CALIFICACION_CONTABLE"
    __table_args__ = {"schema": "CREDITO"}

    codigo = Column("CODIGO", NVARCHAR(30), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(150), nullable=False)
    siglas = Column("SIGLAS", NVARCHAR(10), nullable=False)
    dias_traspaso = Column("DIAS_TRASPASO", Integer, nullable=False)
    calculo_pi = Column("CALCULO_PI", DECIMAL(18, 2), nullable=False)
    codigo_cuenta_deudora = Column("CODIGOCUENTADEUDORA", NVARCHAR(50), nullable=False)
    codigo_cuenta_acreedora = Column("CODIGOCUENTAACREEDORA", NVARCHAR(50), nullable=False)
    normal = Column("NORMAL", Boolean, nullable=False)
    novacion = Column("NOVACION", Boolean, nullable=False)
    refinanciamiento = Column("REFINANCIAMIENTO", Boolean, nullable=False)
    reestructuracion = Column("REESTRUCTURACION", Boolean, nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
