from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Empresa(Base):
    __tablename__ = "EMPRESA"
    __table_args__ = {"schema": "GENERAL"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    codigo = Column("CODIGO", String(10), nullable=False)
    nombre = Column("NOMBRE", String(150), nullable=False)
    id_moneda_principal = Column("IDMONEDAPRINCIPAL", Integer, ForeignKey("GENERAL.MONEDA.ID"), nullable=False)
    id_pais = Column("IDPAIS", Integer, ForeignKey("GENERAL.PAIS.ID"), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
    es_produccion = Column("ESPRODUCCION", Boolean, nullable=False, default=False)

    # Relaciones
    # moneda_principal = relationship("Moneda", back_populates="empresas")
    pais = relationship("Pais", back_populates="empresa")

    # Si quieres tener acceso a agencias relacionadas
    agencia = relationship("Agencia", back_populates="empresa")
    tipos_cuenta = relationship("TipoCuenta", back_populates="empresa")
    transacciones = relationship("Transaccion", back_populates="empresa")
    honorarios_cobranza = relationship("HonorariosCobranza", back_populates="empresa")
