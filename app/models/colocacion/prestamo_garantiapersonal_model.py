from sqlalchemy import Column, Integer, Boolean, ForeignKey, Index
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import relationship

from app.db.base import Base


class PrestamoGarantiaPersonal(Base):
    __tablename__ = "PRESTAMO_GARANTIAPERSONAL"
    __table_args__ = (
        Index(
            "IX_PRESTAMO_GARANTIAPERSONAL_IDPRESTAMO",
            "IDPRESTAMO"
        ),
        {"schema": "COLOCACION"},
    )

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_prestamo = Column("IDPRESTAMO",Integer,ForeignKey("COLOCACION.PRESTAMO.ID"),nullable=False,)
    id_cliente = Column("IDCLIENTE",Integer,ForeignKey("CLIENTES.CLIENTE.ID"),nullable=False,)
    codigo_estado_garantia = Column("CODIGOESTADOGARANTIA",NVARCHAR(10),ForeignKey("COLOCACION.ESTADO_PRESTAMO_GARANTIA.CODIGO"),nullable=False,)
    activo = Column("ACTIVO", Boolean, nullable=False)

    # Relaciones (puedes activarlas si manejas back_populates en los otros modelos)
    prestamos = relationship("Prestamo", back_populates="prestamo_garantias_personales")
    clientes = relationship("Cliente", back_populates="prestamo_garantias_personales")
    # estado_garantia = relationship("EstadoPrestamoGarantia", back_populates="prestamo_garantias_personales")