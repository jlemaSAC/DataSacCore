from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from app.db.base import Base


class Persona(Base):
    __tablename__ = "PERSONA"
    __table_args__ = {"schema": "SUJETO"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    identificacion = Column("IDENTIFICACION", String(20), nullable=False)
    id_tipo_identificacion = Column("IDTIPOIDENTIFICACION", Integer, ForeignKey("SUJETO.TIPO_IDENTIFICACION.ID"), nullable=False)
    nombre = Column("NOMBRE", String(150), nullable=False)
    referencia = Column("REFERENCIA", String(250), nullable=False)
    email = Column("EMAIL", String(150), nullable=False)
    id_pais = Column("IDPAIS", Integer, ForeignKey("GENERAL.PAIS.ID"), nullable=False)
    id_actividad_economica = Column("IDACTIVIDADECONOMICA", Integer, ForeignKey("GENERAL.ACTIVIDAD_ECONOMICA.ID"), nullable=False)
    id_residencia = Column("IDRESIDENCIA", Integer, ForeignKey("GENERAL.DIVISION_POLITICA.ID"), nullable=False)
    usuario_ingreso = Column("USUARIOINGRESO", String(100), ForeignKey("SEGURIDAD.USUARIO.USUARIO"), nullable=False)
    activos = Column("ACTIVOS", DECIMAL(18, 2), nullable=False, default=0)
    pasivos = Column("PASIVOS", DECIMAL(18, 2), nullable=False, default=0)
    ingresos = Column("INGRESOS", DECIMAL(18, 2), nullable=False, default=0)
    egresos = Column("EGRESOS", DECIMAL(18, 2), nullable=False, default=0)
    numero_casa = Column("NUMEROCASA", String(150), nullable=False)
    detalle_casa = Column("DETALLECASA", String(250), nullable=False)
    barrio = Column("BARRIO", String(150), nullable=False)
    calle_principal = Column("CALLEPRINCIPAL", String(500), nullable=False)
    calle_secundaria = Column("CALLESECUNDARIA", String(150), nullable=False)
    codigo_postal = Column("CODIGOPOSTAL", String(10), nullable=True)
    identificacion_sha1 = Column("IDENTIFICACIONSHA1", String(100), nullable=True, default='')

    clientes = relationship("Cliente", back_populates="personas")

    persona_natural = relationship("PersonaNatural", back_populates="personas")
    persona_telefonos = relationship("PersonaTelefono", back_populates="personas")
    # tipo_identificacion = relationship("TipoIdentificacion", backref="personas")
    # actividad_economica = relationship("ActividadEconomica", backref="personas")
    # pais = relationship("Pais", backref="personas")
    # residencia = relationship("DivisionPolitica", backref="personas")
    # usuario = relationship("Usuario", backref="personas")