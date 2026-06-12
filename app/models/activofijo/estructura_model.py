from sqlalchemy import Boolean, Column, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class Estructura(Base):
    __tablename__ = "ESTRUCTURA"
    __table_args__ = {"schema": "ACTIVOFIJO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo = Column("CODIGO", NVARCHAR(50), nullable=False)
    codigo_nivel_estructura = Column(
        "CODIGONIVELESTRUCTURA",
        NVARCHAR(50),
        ForeignKey("ACTIVOFIJO.ESTRUCTURA_NIVEL.CODIGO"),
        nullable=False,
    )
    detalle = Column("DETALLE", NVARCHAR(150), nullable=False)
    se_reexpresa = Column("SEREEXPRESA", Boolean, nullable=False)
    se_deprecia = Column("SEDEPRECIA", Boolean, nullable=False)
    codigo_cuenta_contable_activo = Column(
        "CODIGOCUENTACONTABLEACTIVO",
        NVARCHAR(50),
        ForeignKey("CONTABILIDAD.CUENTACONTABLE.CODIGO"),
        nullable=False,
    )
    codigo_cuenta_contable_deprecia = Column(
        "CODIGOCUENTACONTABLEDEPRECIA",
        NVARCHAR(50),
        ForeignKey("CONTABILIDAD.CUENTACONTABLE.CODIGO"),
        nullable=False,
    )
    codigo_cuenta_contable_gasto = Column(
        "CODIGOCUENTACONTABLEGASTO",
        NVARCHAR(50),
        ForeignKey("CONTABILIDAD.CUENTACONTABLE.CODIGO"),
        nullable=False,
    )
    codigo_cuenta_contable_baja = Column(
        "CODIGOCUENTACONTABLEBAJA",
        NVARCHAR(50),
        ForeignKey("CONTABILIDAD.CUENTACONTABLE.CODIGO"),
        nullable=False,
    )
    codigo_cuenta_contable_total_deprecia = Column(
        "CODIGOCUENTACONTABLETOTALDEPRECIA",
        NVARCHAR(50),
        ForeignKey("CONTABILIDAD.CUENTACONTABLE.CODIGO"),
        nullable=False,
    )
    porcentaje_depreciacion = Column("PORCENTAJEDEPRECIACION", Numeric(18, 2), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
    es_bien_intangible = Column("ESBIENINTANGIBLE", Boolean, nullable=False)
    codigo_cuenta_contable_orden_deudora = Column(
        "CODIGOCUENTACONTABLEORDENDEUDORA",
        NVARCHAR(50),
        ForeignKey("CONTABILIDAD.CUENTACONTABLE.CODIGO"),
        nullable=True,
    )
    codigo_cuenta_contable_orden_acreedora = Column(
        "CODIGOCUENTACONTABLEORDENACREEDORA",
        NVARCHAR(50),
        ForeignKey("CONTABILIDAD.CUENTACONTABLE.CODIGO"),
        nullable=True,
    )
