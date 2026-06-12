from sqlalchemy import Boolean, Column, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class TipoGarantia(Base):
    __tablename__ = "TIPO_GARANTIA"
    __table_args__ = {"schema": "CREDITO"}

    codigo = Column("CODIGO", NVARCHAR(30), primary_key=True, nullable=False)
    siglas = Column("SIGLAS", NVARCHAR(10), nullable=False)
    detalle = Column("DETALLE", NVARCHAR(150), nullable=False)
    codigo_cuenta_orden_deudora = Column(
        "CODIGOCUENTAORDENDEUDORA",
        NVARCHAR(50),
        ForeignKey("CONTABILIDAD.CUENTACONTABLE.CODIGO"),
        nullable=False,
    )
    codigo_cuenta_orden_acreedora = Column(
        "CODIGOCUENTAORDENACREEDORA",
        NVARCHAR(50),
        ForeignKey("CONTABILIDAD.CUENTACONTABLE.CODIGO"),
        nullable=False,
    )
    es_hipotecaria = Column("ESHIPOTECARIA", Boolean, nullable=False)
    es_prendaria = Column("ESPRENDARIA", Boolean, nullable=False)
    es_personal = Column("ESPERSONAL", Boolean, nullable=False)
    es_cheque = Column("ESCHEQUE", Boolean, nullable=False)
    es_deposito_plazo_fijo = Column("ESDEPOSITOPLAZOFIJO", Boolean, nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
