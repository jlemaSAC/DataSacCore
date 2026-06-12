

from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, ForeignKey
from app.db.base import Base

class DetalleS01(Base):
    __tablename__ = "DETALLE_S01"
    __table_args__ = {"schema": "REPORTECONTROL"}

    id = Column('ID', Integer, primary_key=True, autoincrement=True)
    idcabecera = Column('IDCABECERA', Integer, ForeignKey('REPORTECONTROL.CABECERA_S01.ID'), nullable=False)

    tipo_identificacion = Column('TIPOIDENTIFICACION', String(5), nullable=False)
    numero_identificacion = Column('NUMEROIDENTIFICACION', String(13), nullable=False)
    clasificacion_sujeto = Column('CLASIFICACIONSUJETO', String(5), nullable=False)
    pais_nacimiento = Column('PAISNACIMIENTO', String(10), nullable=False)
    tipo_persona = Column('TIPOPERSONA', String(5), nullable=False)
    primer_nombre = Column('PRIMERNOMBRE', String(200), nullable=False)
    segundo_nombre = Column('SEGUNDONOMBRE', String(100), nullable=False)
    primer_apellido = Column('PRIMERAPELLIDO', String(100), nullable=False)
    segundo_apellido = Column('SEGUNDOAPELLIDO', String(100), nullable=False)
    fecha_nacimiento = Column('FECHANACIMIENTO', DateTime, nullable=True)
    genero = Column('GENERO', String(5), nullable=False)
    num_cuenta_certif_aportacion = Column('NUMCUENTACERTIFAPORTACION', String(25), nullable=False)
    estado_socio = Column('ESTADOSOCIO', String(5), nullable=False)
    motivo_ingsal = Column('MOTIVOINGSAL', String(5), nullable=False)
    valor_certif_aport_ant = Column('VALORCERTIFAPORTPERIODOANT', DECIMAL(18, 2), nullable=False)
    valor_certif_aport_act = Column('VALORCERTIFAPORTPERIODOACT', DECIMAL(18, 2), nullable=False)
    fecha_ingreso_salida = Column('FECHAINGRESOSALIDA', DateTime, nullable=True)
    fecha_aprobacion_consejo = Column('FECHA_APROBACIONCONSEJO', DateTime, nullable=True)
    fecha_registro = Column('FECHAREGISTRO', DateTime, nullable=False)
    representante_asamblea = Column('REPRESENTANTEASAMBLEA', String(5), nullable=False)
    fecha_representante_asamblea = Column('FECHAREPRESENTANTEASAMBLEA', DateTime, nullable=True)
    directivo = Column('DIRECTIVO', String(2), nullable=True)
    fecha_directivo = Column('FECHADIRECTIVO', DateTime, nullable=True)

