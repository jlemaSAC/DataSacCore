from sqlalchemy import Boolean, Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.mssql import VARCHAR

from app.db.base import Base


class BanredEntidad(Base):
    __tablename__ = "ENTIDAD"
    __table_args__ = (
        UniqueConstraint("InstitucionID", name="UQ_ENTIDAD_InstitucionID"),
        {"schema": "BANRED"},
    )

    numero = Column("NUMERO", VARCHAR(5), primary_key=True, nullable=False)
    institucion_id = Column(
        "InstitucionID",
        Integer,
        ForeignKey("AHORROS.TRANSFERENCIA_INSTITUCION.ID"),
        nullable=True,
    )
    sigla = Column("SIGLA", VARCHAR(5), nullable=True)
    cod_ordenante = Column("CODORDENANTE", VARCHAR(5), nullable=True)
    cod_receptor = Column("CODRECEPTOR", VARCHAR(5), nullable=True)
    bin = Column("BIN", VARCHAR(10), nullable=True)
    activo = Column("ACTIVO", Boolean, nullable=True)
