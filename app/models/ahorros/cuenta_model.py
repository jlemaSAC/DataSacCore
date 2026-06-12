from sqlalchemy import Column, Integer, String, Boolean, DECIMAL, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from app.db.base import Base


class Cuenta(Base):
    __tablename__ = "CUENTA"
    __table_args__ = {"schema": "AHORROS"}

    # Clave primaria
    numero = Column("NUMERO", String(50), primary_key=True, nullable=False)
    # FKs a catálogos / tablas relacionadas
    codigo_producto = Column("CODIGOPRODUCTO", String(50), ForeignKey("FINANCIERO.PRODUCTO.CODIGO"), nullable=False)
    codigo_tipo_cuenta = Column("CODIGOTIPOCUENTA", String(50), ForeignKey("AHORROS.TIPO_CUENTA.CODIGO"), nullable=False)
    codigo_estado = Column("CODIGOESTADO", String(50), ForeignKey("AHORROS.ESTADO_CUENTA.CODIGO"), nullable=False)
    id_agencia = Column("IDAGENCIA", Integer, ForeignKey("GENERAL.AGENCIA.ID"), nullable=False)
    id_moneda = Column("IDMONEDA", Integer, ForeignKey("GENERAL.MONEDA.ID"), nullable=False)
    nombre_cuenta = Column("NOMBRECUENTA", String(150), nullable=False)
    fechafindia = Column("FECHAFINDIA", DateTime, nullable=False)
    codigo_usuario_oficial = Column("CODIGOUSUARIOOFICIAL", String(100), ForeignKey("SEGURIDAD.USUARIO.USUARIO"), nullable=False)
    codigo_usuario_creacion = Column("CODIGOUSUARIOCREACION", String(100), ForeignKey("SEGURIDAD.USUARIO.USUARIO"), nullable=False)
    fecha_creacion = Column("FECHACREACION", DateTime, nullable=False)
    id_agencia_creacion = Column("IDAGENCIACREACION", Integer, ForeignKey("GENERAL.AGENCIA.ID"), nullable=False)
    codigo_libreta_actual = Column("CODIGOLIBRETAACTUAL", String(50), nullable=False)
    numero_libreta = Column("NUMEROLIBRETA", Integer, nullable=False)
    numero_linea_imprime_libreta_actual = Column("NUMEROLINEAIMPRIMELIBRETAACTUAL", Integer, nullable=False)
    imprime_anverso_libreta_actual = Column("IMPRIMEANVERSOLIBRETAACTUAL", Boolean, nullable=False)
    bloqueo_transaccion = Column("BLOQUEOTRANSACCION", Boolean, nullable=False)
    fecha_ultima_transaccion = Column("FECHAULTIMATRANSACCION", DateTime, nullable=False)
    fecha_ultima_transaccion_activa = Column("FECHAULTIMATRANSACCIONACTIVA", DateTime, nullable=True)
    version = Column("VERSION", LargeBinary, nullable=True)
    saldo_promedio_mensual = Column("SALDOPROMEDIOMENSUAL", DECIMAL(18, 2), nullable=False)
    saldo_promedio_semestral = Column("SALDOPROMEDIOSEMESTRAL", DECIMAL(18, 2), nullable=False)
    
    
        # Agencia “titular”
    agencia = relationship("Agencia", foreign_keys=[id_agencia], back_populates="cuentas_agencia")
    agencia_creacion = relationship("Agencia", foreign_keys=[id_agencia_creacion], back_populates="cuentas_creadas_en_agencia")
    
    # moneda = relationship("Moneda",back_populates="cuentas")
    # estado = relationship("EstadoCuenta",back_populates="cuentas")
    tipos_cuenta = relationship("TipoCuenta",back_populates="cuentas")
    # producto = relationship("Producto",back_populates="cuentas")
    usuario_oficial = relationship(
        "Usuario",
        foreign_keys=[codigo_usuario_oficial],
        back_populates="cuentas_oficial",
    )
    usuario_creacion = relationship(
        "Usuario",
        foreign_keys=[codigo_usuario_creacion],
        back_populates="cuentas_creadas",
    )
    
    cuenta_movimiento_transaccion_detalle = relationship("CuentaMovimientoTransaccionDetalle",back_populates="cuentas") 
    cuentas_clientes = relationship("CuentaCliente", back_populates="cuentas")
    estado_cuenta = relationship("EstadoCuenta", back_populates="cuentas")