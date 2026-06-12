from sqlalchemy import Column, String, Boolean, CHAR
from sqlalchemy.orm import relationship
from app.db.base import Base


class EstadoCuenta(Base):
    __tablename__ = "ESTADO_CUENTA"
    __table_args__ = {"schema": "AHORROS"}

    codigo = Column("CODIGO", String(50), primary_key=True, nullable=False)
    nombre = Column("NOMBRE", String(150), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
    codigo_sarf = Column("CODIGOSARF", CHAR(1), nullable=True)

    # Relaciones (si deseas usarlas en CuentaMovimientoTransaccionDetalle o Cuenta)
    cuentas = relationship("Cuenta", back_populates="estado_cuenta")
    # cuentas_movimiento_detalle = relationship(
    #     "CuentaMovimientoTransaccionDetalle",
    #     back_populates="estado_cuenta",
    #     lazy="selectin"
    # )