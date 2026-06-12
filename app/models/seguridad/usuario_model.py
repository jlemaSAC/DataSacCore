from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import relationship
from app.db.base import Base



class Usuario(Base):
    __tablename__ = "USUARIO"
    __table_args__ = {"schema": "SEGURIDAD"}

    usuario = Column("USUARIO",NVARCHAR(100), primary_key=True, nullable=False)
    nombre = Column("NOMBRE",NVARCHAR(150), nullable=False)
    clave = Column("CLAVE",NVARCHAR(None), nullable=False) 
    id_agencia = Column("IDAGENCIA",Integer, ForeignKey("GENERAL.AGENCIA.ID"), nullable=False)
    email = Column("EMAIL",NVARCHAR(200), nullable=False)
    fecha_creacion = Column("FECHACREACION",DateTime, nullable=False)
    fecha_cambio_clave = Column("FECHACAMBIOCLAVE",DateTime, nullable=False)
    cambia_clave = Column("CAMBIACLAVE",Boolean, nullable=False)
    dias_cambio_clave = Column("DIASCAMBIOCLAVE",Integer, nullable=False)
    tiene_bloqueo = Column("TIENEBLOQUEO",Boolean, nullable=False)
    puede_ingresar_sistema = Column("PUEDEINGRESARSISTEMA",Boolean, nullable=False)
    activo = Column("ACTIVO",Boolean, nullable=False)
    sesion_unica = Column("SESIONUNICA",Boolean, nullable=False, default=False)

    
    agencia = relationship("Agencia", back_populates="usuario")
    usuario_roles = relationship("UsuarioRol", back_populates="usuario")
    empleados_usuarios = relationship("EmpleadoUsuario", back_populates="usuario")
    empleados = relationship("Empleado", back_populates="usuario")  
    prestamo_rubro_detalle = relationship("PrestamoRubroAdicionalDetalle",back_populates="usuario")
    movimiento_transaccion_detalles_referido = relationship("MovimientoTransaccionDetalleReferido",back_populates="usuario")
    cuentas_oficial = relationship("Cuenta", back_populates="usuario_oficial", foreign_keys="Cuenta.codigo_usuario_oficial")
    cuentas_creadas = relationship("Cuenta", back_populates="usuario_creacion", foreign_keys="Cuenta.codigo_usuario_creacion")
    prestamo_calificaciones=relationship("PrestamoCalificacion", back_populates="usuario")
    prestamos_usuario_control = relationship("PrestamoUsuarioControl", back_populates="usuario_control")
