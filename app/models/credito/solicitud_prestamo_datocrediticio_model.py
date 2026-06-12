from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.mssql import DECIMAL, NVARCHAR

from app.db.base import Base


class SolicitudPrestamoDatoCrediticio(Base):
    __tablename__ = "SOLICITUD_PRESTAMO_DATOCREDITICIO"
    __table_args__ = {"schema": "CREDITO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_solicitud_prestamo = Column(
        "IDSOLICITUDPRESTAMO",
        Integer,
        ForeignKey("CREDITO.SOLICITUD_PRESTAMO.ID"),
        nullable=False,
    )
    id_cliente = Column(
        "IDCLIENTE",
        Integer,
        ForeignKey("CLIENTES.CLIENTE.ID"),
        nullable=False,
    )
    id_actividad_economica = Column(
        "IDACTIVIDADECONOMICA",
        Integer,
        ForeignKey("GENERAL.ACTIVIDAD_ECONOMICA.ID"),
        nullable=True,
    )
    descripcion_actividad = Column("DESCRIPCIONACTIVIDAD", NVARCHAR(600), nullable=False)
    numero_meses_actividad = Column("NUMEROMESESACTIVIDAD", Integer, nullable=False)
    arrendador_vivienda = Column("ARRENDADORVIVIENDA", NVARCHAR(100), nullable=False)
    total_ingresos = Column("TOTALINGRESOS", DECIMAL(18, 2), nullable=True)
    total_gastos = Column("TOTALGASTOS", DECIMAL(18, 2), nullable=True)
    total_activos = Column("TOTALACTIVOS", DECIMAL(18, 2), nullable=True)
    total_pasivos = Column("TOTALPASIVOS", DECIMAL(18, 2), nullable=True)
    dias_ultimo_prestamo = Column("DIASULTIMOPRESTAMO", Integer, nullable=False)
    dias_penultimo_prestamo = Column("DIASPENULTIMOPRESTAMO", Integer, nullable=False)
    calificacion_buro = Column("CALIFICACIONBURO", NVARCHAR(10), nullable=False)
    valor_cuota = Column("VALORCUOTA", DECIMAL(18, 2), nullable=False)
    numero_cargas = Column("NUMEROCARGAS", Integer, nullable=False)
    porcentaje_negocio = Column("PORCENTAJENEGOCIO", DECIMAL(18, 2), nullable=False)
    fecha_sistema = Column("FECHASISTEMA", DateTime, nullable=False)
    fecha_proceso = Column("FECHAPROCESO", DateTime, nullable=False)
    codigo_usuario = Column(
        "CODIGOUSUARIO",
        NVARCHAR(100),
        ForeignKey("SEGURIDAD.USUARIO.USUARIO"),
        nullable=False,
    )

