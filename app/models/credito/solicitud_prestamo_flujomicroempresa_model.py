from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mssql import DECIMAL, NVARCHAR

from app.db.base import Base


class SolicitudPrestamoFlujoMicroempresa(Base):
    __tablename__ = "SOLICITUD_PRESTAMO_FLUJOMICROEMPRESA"
    __table_args__ = {"schema": "CREDITO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_solicitud_prestamo = Column(
        "IDSOLICITUDPRESTAMO",
        Integer,
        ForeignKey("CREDITO.SOLICITUD_PRESTAMO.ID"),
        nullable=False,
    )
    id_microempresa = Column(
        "IDMICROEMPRESA",
        Integer,
        ForeignKey("CLIENTES.MICROEMPRESA.ID"),
        nullable=False,
    )
    codigo_tipo_periodo = Column(
        "CODIGOTIPOPERIODO",
        NVARCHAR(10),
        ForeignKey("CREDITO.TIPO_PERIODO.CODIGO"),
        nullable=False,
    )
    total_activos = Column("TOTALACTIVOS", DECIMAL(18, 2), nullable=False)
    total_pasivos = Column("TOTALPASIVOS", DECIMAL(18, 2), nullable=False)
    total_ventas = Column("TOTALVENTAS", DECIMAL(18, 2), nullable=False)
    total_costo_fijo = Column("TOTALCOSTOFIJO", DECIMAL(18, 2), nullable=False)
    total_costo_variable = Column("TOTALCOSTOVARIABLE", DECIMAL(18, 2), nullable=False)
    fecha_sistema = Column("FECHASISTEMA", DateTime, nullable=False)
    fecha_proceso = Column("FECHAPROCESO", DateTime, nullable=False)
    codigo_usuario = Column(
        "CODIGOUSUARIO",
        NVARCHAR(100),
        ForeignKey("SEGURIDAD.USUARIO.USUARIO"),
        nullable=False,
    )
    experiencia_negocio = Column("EXPERIENCIANEGOCIO", Integer, nullable=False)
    tiempo_en_local = Column("TIEMPOENLOCAL", Integer, nullable=False)
    horario_atencion = Column("HORARIOATENCION", NVARCHAR(500), nullable=False)
    meses_actividad_economica = Column("MESESACTIVIDADECONOMICA", Integer, nullable=True)

