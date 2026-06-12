from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Cliente(Base):
    __tablename__ = "CLIENTE"
    __table_args__ = {"schema": "CLIENTES"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    numero = Column("NUMERO", Integer, nullable=False)
    id_agencia = Column("IDAGENCIA", Integer, ForeignKey("GENERAL.AGENCIA.ID"), nullable=False)
    id_persona = Column("IDPERSONA", Integer, ForeignKey("SUJETO.PERSONA.ID"), nullable=False)
    fecha_ingreso = Column("FECHAINGRESO", DateTime, nullable=False)
    usuario_creacion = Column("USUARIOCREACION", String(100), ForeignKey("SEGURIDAD.USUARIO.USUARIO"), nullable=False)
    usuario_oficial = Column("USUARIOOFICIAL", String(100), ForeignKey("SEGURIDAD.USUARIO.USUARIO"), nullable=False)
    codigo_calificacion_interna = Column("CODIGOCALIFICACIONINTERNA", String(20), ForeignKey("CLIENTES.CALIFICACION_INTERNA.CODIGO"), nullable=False)
    codigo_causa_vinculacion = Column("CODIGOCAUSAVINCULACION", String(20), ForeignKey("CLIENTES.CAUSAVINCULACION.CODIGO"), nullable=False)
    codigo_sector_economico = Column("CODIGOSECTORECONOMICO", String(20), ForeignKey("CLIENTES.SECTOR_ECONOMICO.CODIGO"), nullable=False)
    codigo_estado = Column("CODIGOESTADO", String(20), ForeignKey("CLIENTES.ESTADOCLIENTE.CODIGO"), nullable=False)
    es_excento = Column("ESEXCENTO", Boolean, nullable=False)

    
    personas = relationship("Persona", back_populates="clientes")
    prestamos_clientes = relationship("PrestamoCliente", back_populates="clientes")
    cuentas_clientes = relationship("CuentaCliente", back_populates="clientes")
    prestamo_garantias_personales = relationship("PrestamoGarantiaPersonal", back_populates="clientes")
    # agencia = relationship("Agencia", backref="clientes")
    # calificacion_interna = relationship("CalificacionInterna", backref="clientes")
    # causa_vinculacion = relationship("CausaVinculacion", backref="clientes")
    # sector_economico = relationship("SectorEconomico", backref="clientes")
    # estado_cliente = relationship("EstadoCliente", backref="clientes")
    # usuario_creador = relationship("Usuario", foreign_keys=[usuario_creacion], backref="clientes_creados")
    # usuario_oficial_rel = relationship("Usuario", foreign_keys=[usuario_oficial], backref="clientes_asignados")