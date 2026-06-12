from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base



class Usuario(Base):
    __tablename__ = "USUARIO"
    __table_args__ = {"schema": "SEGURIDAD"}

    usuario = Column('USUARIO', NVARCHAR(100), primary_key=True, nullable=False)
    nombre = Column('NOMBRE', NVARCHAR(150), nullable=False)
    clave = Column('CLAVE', NVARCHAR(None), nullable=False) 
    id_agencia = Column('IDAGENCIA', Integer, ForeignKey('GENERAL.AGENCIA.ID'), nullable=False)
    email = Column('EMAIL', NVARCHAR(200), nullable=False)
    fecha_creacion = Column('FECHACREACION', DateTime, nullable=False)
    fecha_cambio_clave = Column('FECHACAMBIOCLAVE', DateTime, nullable=False)
    cambia_clave = Column('CAMBIACLAVE', Boolean, nullable=False)
    dias_cambio_clave = Column('DIASCAMBIOCLAVE', Integer, nullable=False)
    tiene_bloqueo = Column('TIENEBLOQUEO', Boolean, nullable=False)
    puede_ingresar_sistema = Column('PUEDEINGRESARSISTEMA', Boolean, nullable=False)
    activo = Column('ACTIVO', Boolean, nullable=False)
    sesion_unica = Column('SESIONUNICA', Boolean, nullable=False, default=False)

    
