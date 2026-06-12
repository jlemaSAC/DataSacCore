from sqlalchemy import (
    Column, Integer, String, Boolean, DECIMAL, ForeignKey
)
from sqlalchemy.orm import relationship
from app.db.base import Base

class Rubro(Base):
    __tablename__ = "RUBRO"
    __table_args__ = {"schema": "COLOCACION"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True)
    codigo_tipo_rubro = Column("CODIGOTIPORUBRO", String(10), ForeignKey("COLOCACION.TIPO_RUBRO.CODIGO"), nullable=False)
    nombre = Column("NOMBRE", String(150), nullable=False)
    es_calculo_adicional = Column("ESCALCULOADICIONAL", Boolean, nullable=False)
    genera_adjudicacion = Column("GENERAADJUDICACION", Boolean, nullable=False)
    es_cuenta_por_cobrar = Column("ESCUENTAPORCOBRAR", Boolean, nullable=False)
    orden_de_cobro = Column("ORDENDECOBRO", Integer, nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)
    se_factura = Column("SEFACTURA", Boolean, nullable=False)
    tarifa_impuesto = Column("TARIFAIMPUESTO", DECIMAL(18, 2), nullable=False)
    permite_castigo = Column("PERMITECASTIGO", Boolean, nullable=False, default=True)

    # Relaciones (opcional si las usas)
    prestamos_rubros = relationship("PrestamoRubro", back_populates="rubros")
    rubro_cuenta_contable = relationship("RubroCuentaContable", back_populates="rubros")
    tipo_rubro = relationship("TipoRubro", back_populates="rubros")