from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base


class Cargo(Base):
    __tablename__ = "CARGO"
    __table_args__ = {"schema": "NOMINA"}

    id = Column("ID", Integer, primary_key=True, autoincrement=True, nullable=False)
    nombre = Column("NOMBRE", String(150), nullable=False, unique=True)
    activo = Column("ACTIVO", Boolean, nullable=False)
    es_vinculado = Column("ESVINCULADO", Boolean, nullable=True)

    # Relaciones (si en el futuro se conecta con otras tablas)
    # ejemplo: empleados = relationship("Empleado", back_populates="cargo")