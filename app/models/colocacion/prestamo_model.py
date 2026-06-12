from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, DECIMAL, ForeignKey, LargeBinary
)
from sqlalchemy.orm import relationship
from app.db.base import Base

class Prestamo(Base):
    __tablename__ = "PRESTAMO"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    numero = Column("NUMERO", String(50), nullable=False)
    numero_pagare = Column("NUMERO_PAGARE", String(50), nullable=False)
    codigo_producto = Column("CODIGOPRODUCTO", String(50), ForeignKey("FINANCIERO.PRODUCTO.CODIGO"), nullable=False)
    codigo_tipo_prestamo = Column("CODIGOTIPOPRESTAMO", String(30), ForeignKey("CREDITO.TIPO_PRESTAMO.CODIGO"), nullable=False)
    id_empresa = Column("IDEMPRESA", Integer, ForeignKey("GENERAL.EMPRESA.ID"), nullable=False)
    id_agencia = Column("IDAGENCIA", Integer, ForeignKey("GENERAL.AGENCIA.ID"), nullable=False)
    codigo_usuario = Column("CODIGOUSUARIO", String(100), ForeignKey("SEGURIDAD.USUARIO.USUARIO"), nullable=False)
    codigo_usuario_creacion = Column("CODIGOUSUARIOCREACION", String(100), ForeignKey("SEGURIDAD.USUARIO.USUARIO"), nullable=False)
    id_calificacion_contable_segmento = Column("IDCALIFICACIONCONTABLESEGMENTO", Integer, ForeignKey("CREDITO.CALIFICACION_CONTABLE_SEGMENTO.ID"), nullable=False)
    codigo_subcalificacion_contable = Column("CODIGOSUBCALIFICACIONCONTABLE", String(30), ForeignKey("CREDITO.SUBCALIFICACION_CONTABLE.CODIGO"), nullable=False)
    id_tipo_tabla_amortizacion = Column("IDTIPOTABLAAMORTIZACION", Integer, ForeignKey("CREDITO.TIPO_TABLA_AMORTIZACION.ID"), nullable=False)
    codigo_origen_recurso = Column("CODIGOORIGENRECURSO", String(30), ForeignKey("CREDITO.ORIGEN_RECURSO.CODIGO"), nullable=False)
    id_moneda = Column("IDMONEDA", Integer, ForeignKey("GENERAL.MONEDA.ID"), nullable=False)
    frecuencia_pago = Column("FRECUENCIAPAGO", Integer, nullable=False)
    cuotas = Column("CUOTAS", Integer, nullable=False)
    deuda_inicial = Column("DEUDAINICIAL", DECIMAL(18, 2), nullable=False)
    valor_entregado = Column("VALORENTREGADO", DECIMAL(18, 2), nullable=False)
    fecha_adjudicacion = Column("FECHAADJUDICACION", DateTime, nullable=False)
    fecha_vencimiento = Column("FECHAVENCIMIENTO", DateTime, nullable=False)
    fecha_fin_dia = Column("FECHAFINDIA", DateTime, nullable=False)
    saldo = Column("SALDO", DECIMAL(18, 2), nullable=False)
    tasa = Column("TASA", DECIMAL(18, 2), nullable=False)
    tea = Column("TEA", DECIMAL(18, 2), nullable=False)
    tea_seguro = Column("TEA_SEGURO", DECIMAL(18, 2), nullable=False)
    calificacion = Column("CALIFICACION", String(10), nullable=False)
    calificacion_baja = Column("CALIFICACION_BAJA", String(10), nullable=False)
    cobro_rol = Column("COBROROL", Boolean, nullable=False)
    reajusta_tasa = Column("REAJUSTATASA", Boolean, nullable=False)
    total_dias_reajuste = Column("TOTALDIASREAJUSTE", Integer, nullable=False)
    codigo_estado = Column("CODIGOESTADO", String(10), ForeignKey("COLOCACION.ESTADO_PRESTAMO.CODIGO"), nullable=False)
    tiene_bloque_operativo = Column("TIENEBLOQUEOPERATIVO", Boolean, nullable=False)
    firma_conjunta = Column("FIRMACONJUNTA", Boolean, nullable=False)
    version = Column("VERSION", LargeBinary, nullable=True)  # Para `timestamp` usamos `LargeBinary` en SQLAlchemy

    # Relaciones
    prestamos_clientes = relationship("PrestamoCliente", back_populates="prestamos")
    prestamo_consolidado = relationship("PrestamoConsolidado", back_populates="prestamos")
    
    agencia = relationship("Agencia", back_populates="prestamos")
    estado_prestamo = relationship("EstadoPrestamo", back_populates="prestamos")
    prestamos_rubros = relationship("PrestamoRubro", back_populates="prestamos")
    tipo_prestamo = relationship("TipoPrestamo", back_populates="prestamos")
    prestamo_movimiento_transaccion_detalle = relationship("PrestamoMovimientoTransaccionDetalle", back_populates="prestamos")
    prestamos_solicitud = relationship("PrestamoSolicitud",back_populates="prestamos") 
    cancelaciones_solicitudes = relationship("SolicitudPrestamoCancelaPrestamo", back_populates="prestamos")
    prestamo_calificaciones=relationship("PrestamoCalificacion", back_populates="prestamo")
    prestamo_garantias_personales = relationship("PrestamoGarantiaPersonal", back_populates="prestamos")
    
    # empresa = relationship("Empresa", backref="prestamos")
    # usuario = relationship("Usuario", foreign_keys=[codigo_usuario], backref="prestamos_asignados")
    # usuario_creacion = relationship("Usuario", foreign_keys=[codigo_usuario_creacion], backref="prestamos_creados")
    # moneda = relationship("Moneda", backref="prestamos")
    
    # producto = relationship("Producto", backref="prestamos")
    
    # calificacion_segmento = relationship("CalificacionContableSegmento", backref="prestamos")
    # subcalificacion = relationship("SubcalificacionContable", backref="prestamos")
    # tabla_amortizacion = relationship("TipoTablaAmortizacion", backref="prestamos")
    # origen_recurso = relationship("OrigenRecurso", backref="prestamos")
