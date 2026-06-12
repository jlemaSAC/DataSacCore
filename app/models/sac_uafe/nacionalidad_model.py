from sqlalchemy import Column, String, Boolean, CHAR
from sqlalchemy.orm import relationship
from app.db.base import Base


class Nacionalidad(Base):
    __tablename__ = "NACIONALIDAD"
    __table_args__ = {"schema": "SAC_UAFE"}

    codigo = Column("CODIGO", CHAR(3), primary_key=True, nullable=False)
    descripcion = Column("DESCRIPCION", String(100), unique=True, nullable=False)
    esta_activo = Column("ESTAACTIVO", Boolean, nullable=False, default=True)

    # Relaciones
    pais = relationship("Pais", back_populates="nacionalidad")