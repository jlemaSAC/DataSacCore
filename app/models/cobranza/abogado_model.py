from sqlalchemy import Column, Integer, Boolean, DECIMAL, ForeignKey, NVARCHAR
from sqlalchemy.orm import relationship

from app.db.base import Base


class Abogado(Base):
    __tablename__ = "ABOGADO"
    __table_args__ = {"schema": "COBRANZA"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    id_persona = Column("IDPERSONA", Integer, ForeignKey("SUJETO.PERSONA.ID"), nullable=False)
    id_tipo_identificacion = Column(
        "IDTIPOIDENTIFICACION",
        Integer,
        ForeignKey("SUJETO.TIPO_IDENTIFICACION.ID"),
        nullable=False,
    )
    ruc = Column("RUC", NVARCHAR(20, collation="Modern_Spanish_CI_AS"), nullable=False)
    nombre = Column("NOMBRE", NVARCHAR(150, collation="Modern_Spanish_CI_AS"), nullable=False)
    direccion = Column("DIRECCION", NVARCHAR(250, collation="Modern_Spanish_CI_AS"), nullable=False)
    telefono = Column("TELEFONO", NVARCHAR(50, collation="Modern_Spanish_CI_AS"), nullable=False)
    celular = Column("CELULAR", NVARCHAR(50, collation="Modern_Spanish_CI_AS"), nullable=False)
    email = Column("EMAIL", NVARCHAR(150, collation="Modern_Spanish_CI_AS"), nullable=False)
    porcentaje_cobro = Column("PORCENTAJE_COBRO", DECIMAL(18, 2), nullable=False)
    id_empresa = Column("IDEMPRESA", Integer, ForeignKey("GENERAL.EMPRESA.ID"), nullable=False)
    activo = Column("ACTIVO", Boolean, nullable=False)

    # Relaciones
    empresa = relationship("Empresa")
    persona = relationship("Persona")
    prestamos_judiciales = relationship("PrestamoJudicial")
