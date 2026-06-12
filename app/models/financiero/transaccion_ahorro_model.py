from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class TransaccionAhorros(Base):
    __tablename__ = "TRANSACCION_AHORROS"
    __table_args__ = {"schema": "FINANCIERO"}

    id_transaccion = Column(
        "IDTRANSACCION",
        Integer,
        ForeignKey("FINANCIERO.TRANSACCION.ID"),
        primary_key=True,
        nullable=False,
    )

    es_cierre_cuenta = Column("ESCIERRECUENTA", Boolean, nullable=False)
    es_apertura_cuenta = Column("ESAPERTURACUENTA", Boolean, nullable=False)
    activa_cuenta_inactiva = Column("ACTIVACUENTAINACTIVA", Boolean, nullable=False)
    es_encaje_prestamo = Column("ESENCAJEPRESTAMO", Boolean, nullable=False)
    es_dese_encaje_prestamo = Column("ESDESENCAJEPRESTAMO", Boolean, nullable=False)
    es_bloqueo = Column("ESBLOQUEO", Boolean, nullable=False)
    es_desbloqueo = Column("ESDESBLOQUEO", Boolean, nullable=False)
    es_cobro_diferido = Column("ESCOBRODIFERIDO", Boolean, nullable=False)
    es_transferencia_interes = Column("ESTRANSFERENCIAINTERES", Boolean, nullable=False)
    es_anulacion_plazo_cheque = Column("ESANULACIONPLAZOCHEQUE", Boolean, nullable=False)
    es_en_lote = Column("ESENLOTE", Boolean, nullable=False)
    es_certificado = Column("ESCERTIFICADO", Boolean, nullable=False)
    es_transferencia_en_lote = Column("ESTRANSFERENCIAENLOTE", Boolean, nullable=False)
    es_pago_institucion = Column("ESPAGOINSTITUCION", Boolean, nullable=False)
    es_cobro_programado = Column("ESCOBROPROGRAMADO", Boolean, nullable=False)
    es_transferencia_programado = Column("ESTRANSFERENCIAPROGRAMADO", Boolean, nullable=False)
    es_pago_inversion = Column("ESPAGOINVERSION", Boolean, nullable=False, default=False)
    es_transferencia_programado_vista = Column("ESTRANSFERENCIAPROGRAMADOVISTA", Boolean, nullable=False, default=False)
    verifica_monto_activa_cuenta = Column("VERIFICAMONTOACTIVACUENTA", Boolean, nullable=False, default=False)
    es_transf_programado_restrin = Column("ESTRANSFPROGRAMADORESTRIN", Boolean, nullable=False, default=False)

    # Relación con TRANSACCION
    transacciones = relationship("Transaccion", back_populates="transaccion_ahorros")