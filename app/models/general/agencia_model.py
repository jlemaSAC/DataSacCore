from sqlalchemy import Column, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.mssql import NVARCHAR
from app.db.base import Base
from sqlalchemy.orm import relationship



class Agencia(Base):
    __tablename__ = "AGENCIA"
    __table_args__ = {"schema": "GENERAL"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_empresa = Column("IDEMPRESA", Integer, ForeignKey("GENERAL.EMPRESA.ID"), nullable=False)
    id_residencia = Column("IDRESIDENCIA", Integer, ForeignKey("GENERAL.DIVISION_POLITICA.ID"), nullable=False)
    codigo = Column("CODIGO", NVARCHAR(20), nullable=False)
    codigo_super = Column("CODIGOSUPER", NVARCHAR(8), nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(150), nullable=False)
    direccion = Column("DIRECCION", NVARCHAR(250), nullable=True)
    operativa = Column("OPERATIVA", Boolean, nullable=False)
    cierre_contable = Column("CIERRECONTABLE", DateTime, nullable=False)
    activa = Column("ACTIVA", Boolean, nullable=False)
    id_zona = Column("IDZONA", Integer, nullable=False)
    id_region_natural = Column("IDREGIONNATURAL", Integer, nullable=True)
    codigo_ciudad = Column("CODIGOCIUDAD", NVARCHAR(50), ForeignKey("GENERAL.CIUDAD.CODIGO"), nullable=True)
    id_zona_crediticia = Column("IDZONACREDITICIA", Integer, ForeignKey("GENERAL.ZONACREDITICIA.ID"), nullable=False, default=1)
    es_coffee_sac = Column("ESCOFFEESAC", Boolean, nullable=True)
    codigo_activo_fijo = Column("CODIGOACTIVOFIJO", NVARCHAR(5), nullable=False, default='NN')


    usuario = relationship("Usuario", back_populates="agencia")  
    prestamos = relationship("Prestamo", back_populates="agencia")
    movimientos_detalle = relationship("MovimientoTransaccionDetalle", back_populates="agencia")
    
    cuentas_agencia = relationship(
        "Cuenta",
        back_populates="agencia",
        foreign_keys="Cuenta.id_agencia",
        lazy="selectin",
    )
    # Cuentas creadas en esta agencia (AHORROS.CUENTA.IDAGENCIACREACION)
    cuentas_creadas_en_agencia = relationship(
        "Cuenta",
        back_populates="agencia_creacion",
        foreign_keys="Cuenta.id_agencia_creacion",
        lazy="selectin",
    )
    
    empresa = relationship("Empresa", back_populates="agencia")
    
    