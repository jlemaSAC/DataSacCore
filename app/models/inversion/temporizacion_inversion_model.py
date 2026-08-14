from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TemporizacionInversion(Base):
    __tablename__ = "TEMPORIZACION_INVERSION"
    __table_args__ = {"schema": "INVERSION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column(
        "IDEMPRESA", Integer, ForeignKey("GENERAL.EMPRESA.ID"), nullable=False
    )
    dias_inicio = Column("DIASINICIO", Integer, nullable=False)
    dias_fin = Column("DIASFIN", Integer, nullable=False)
    codigo_cuenta_contable = Column(
        "CODIGOCUENTACONTABLE",
        NVARCHAR(50),
        ForeignKey("CONTABILIDAD.CUENTACONTABLE.CODIGO"),
        nullable=False,
    )
    activo = Column("ACTIVO", Boolean, nullable=False)
