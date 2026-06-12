from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mssql import DECIMAL, NVARCHAR
from sqlalchemy.orm import relationship

from app.db.base import Base


class CalificacionPrestamoInformacion(Base):
    __tablename__ = "CALIFICACION_PRESTAMO_INFORMACION"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column(
        "IDEMPRESA",
        Integer,
        ForeignKey("GENERAL.EMPRESA.ID"),
        nullable=False,
    )
    codigo_calificacion_contable = Column(
        "CODIGOCALIFICACIONCONTABLE",
        NVARCHAR(30),
        ForeignKey("CREDITO.CALIFICACION_CONTABLE.CODIGO"),
        nullable=False,
    )
    calificacion = Column("CALIFICACION", NVARCHAR(5), nullable=True)
    dia_inicio = Column("DIAINICIO", Integer, nullable=False)
    dia_fin = Column("DIAFIN", Integer, nullable=False)
    porcentaje_fijo = Column("PORCENTAJE_FIJO", DECIMAL(18, 2), nullable=False)
    porcentaje_minimo = Column("PORCENTAJE_MINIMO", DECIMAL(18, 2), nullable=False)
    porcentaje_maximo = Column("PORCENTAJE_MAXIMO", DECIMAL(18, 2), nullable=False)
    es_porcentaje_fijo = Column("ESPORCENTAJE_FIJO", Boolean, nullable=False)
    codigo_usuario = Column(
        "CODIGOUSUARIO",
        NVARCHAR(100),
        ForeignKey("SEGURIDAD.USUARIO.USUARIO"),
        nullable=False,
    )
    fecha = Column("FECHA", DateTime, nullable=False)
    fecha_proceso = Column("FECHAPROCESO", DateTime, nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)

    empresa = relationship("Empresa")
    calificacion_contable = relationship("CalificacionContable")
    usuario = relationship("Usuario")
