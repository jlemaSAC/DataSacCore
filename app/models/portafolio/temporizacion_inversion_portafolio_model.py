from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import relationship

from app.db.base import Base


class TemporizacionInversionPortafolio(Base):
    __tablename__ = "TEMPORIZACION_INVERSION_PORTAFOLIO"
    __table_args__ = {"schema": "PORTAFOLIO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo_tipo_documento = Column(
        "CODIGOTIPODOCUMENTO",
        NVARCHAR(5),
        ForeignKey("PORTAFOLIO.TIPODOCUMENTO.CODIGO"),
        nullable=False,
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

    inversion_items = relationship("InversionItemInversionTemporizacion", back_populates="temporizacion")

