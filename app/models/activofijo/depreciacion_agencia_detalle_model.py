from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, text
from sqlalchemy.dialects.mssql import NVARCHAR

from app.db.base import Base


class DepreciacionAgenciaDetalle(Base):
    __tablename__ = "DEPRECIACION_AGENCIA_DETALLE"
    __table_args__ = (
        Index("IX_DEPRECIACION_AGENCIA_DETALLE_IDACTIVO", "IDACTIVO"),
        {"schema": "ACTIVOFIJO"},
    )

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_depreciacion_agencia = Column(
        "IDDEPRECIACIONAGENCIA",
        Integer,
        ForeignKey("ACTIVOFIJO.DEPRECIACION_AGENCIA.ID"),
        nullable=False,
    )
    id_activo = Column("IDACTIVO", Integer, ForeignKey("ACTIVOFIJO.ACTIVO.ID"), nullable=False)
    fecha_depreciacion = Column("FECHADEPRECIACION", DateTime, nullable=False)
    fecha_proceso = Column("FECHAPROCESO", DateTime, nullable=False)
    porcentaje_depreciacion_periodo = Column(
        "PORCENTAJEDEPRECIACIONPERIODO",
        Numeric(18, 2),
        nullable=False,
    )
    porcentaje_depreciacion_acumulada = Column(
        "PORCENTAJEDEPRECIACIONACUMULADA",
        Numeric(18, 2),
        nullable=False,
    )
    valor_anterior = Column("VALORANTERIOR", Numeric(18, 2), nullable=False)
    incremento = Column("INCREMENTO", Numeric(18, 2), nullable=False)
    indice_correccion = Column("INDICECORRECCION", Numeric(18, 2), nullable=False)
    depreciacion_acumulada = Column("DEPRECIACIONACUMULADA", Numeric(18, 2), nullable=False)
    depreciacion_periodo = Column("DEPRECIACIONPERIODO", Numeric(18, 2), nullable=False)
    saldo_libros = Column("SALDOLIBROS", Numeric(18, 2), nullable=False)
    depreciado_total = Column("DEPRECIADOTOTAL", Boolean, nullable=False)
    codigo_usuario = Column(
        "CODIGOUSUARIO",
        NVARCHAR(100),
        ForeignKey("SEGURIDAD.USUARIO.USUARIO"),
        nullable=False,
    )
    fecha_inicio_calculo = Column(
        "FECHAINICIOCALCULO",
        DateTime,
        nullable=False,
        server_default=text("getdate()"),
    )
